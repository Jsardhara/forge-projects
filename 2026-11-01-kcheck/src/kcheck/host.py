"""The four local probes: running kernel, installed kernel packages, MPTCP switch, listeners.

Everything here is read-only and local. No network, no root, no package manager: two
``dpkg-query``/``uname`` reads, one ``sysctl`` read, one ``ss`` read. The tool never
writes a sysctl and never calls ``nft``/``iptables`` -- the advisory's mitigation is an
operator decision on a host firewall, and automating it from a checker is how a checker
becomes an outage.

Each probe can fail, and a failure returns ``None`` -- never ``False``, never ``0``.
"Could not look" and "looked, found nothing" are different claims and this module keeps
them apart.
"""

import ipaddress
import os
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple

SYSCTL_KEY = "net.mptcp.enabled"

TAILNET_V4 = ipaddress.ip_network("100.64.0.0/10")
TAILNET_V6 = ipaddress.ip_network("fd7a:115c:a1e0::/48")
PRIVATE_V4 = (ipaddress.ip_network("10.0.0.0/8"),
              ipaddress.ip_network("172.16.0.0/12"),
              ipaddress.ip_network("192.168.0.0/16"),
              ipaddress.ip_network("169.254.0.0/16"))
PRIVATE_V6 = (ipaddress.ip_network("fc00::/7"), ipaddress.ip_network("fe80::/10"))

# Widest exposure first: a security readout must lead with the worst listener, not the
# friendliest one.
SCOPE_ORDER = ("all_interfaces", "public", "private_lan", "tailnet", "localhost", "unknown")

ALL_INTERFACES = ("", "*", "0.0.0.0", "::", "[::]")

FIXTURE_FILES = {
    "uname": "uname.txt",
    "dpkg": "dpkg.txt",
    "sysctl": "sysctl.txt",
    "ss": "ss.txt",
    "os_release": "os-release.txt",
}

COMMANDS = {
    "uname": ("uname", "-r"),
    "dpkg": ("dpkg-query", "-W", "-f=${Package} ${Version}\n", "linux-image-*"),
    "sysctl": ("sysctl", SYSCTL_KEY),
    "ss": ("ss", "-Mln"),
}

PROBE_TIMEOUT = 5.0


@dataclass(frozen=True)
class Listener:
    address: str
    port: str
    scope: str
    network: str


@dataclass(frozen=True)
class HostFacts:
    """Measured host state. ``None`` always means unmeasurable, never the safe default."""

    release: Optional[str] = None
    package_name: Optional[str] = None
    package_version: Optional[str] = None
    kernel_images: Tuple[str, ...] = ()
    mptcp_enabled: Optional[bool] = None
    mptcp_listeners: Optional[Tuple[Listener, ...]] = None
    distro: str = ""
    distro_release: str = ""
    distro_codename: str = ""
    errors: Tuple[str, ...] = ()

    @property
    def exposure_surface(self):
        if self.mptcp_listeners is None:
            return ()
        return exposure_surface(self.mptcp_listeners)


def parse_dpkg(text):
    """``dpkg-query -W -f='${Package} ${Version}\\n'`` -> {package: version or None}.

    Two packages on this host legitimately print an empty version (half-installed),
    which is why ``len(parts) == 1`` maps to ``None`` instead of to a package whose
    version happens to be the next token.
    """
    packages = {}
    for line in (text or "").splitlines():
        parts = line.split()
        if not parts or parts[0].endswith(":"):
            continue  # stderr noise such as "dpkg-query: warning: ..."
        packages[parts[0]] = parts[1] if len(parts) > 1 else None
    return packages


def package_for_release(packages, release):
    """(package, version) for the running release, or None when it is not installed."""
    if not release:
        return None
    name = "linux-image-%s" % release
    version = packages.get(name)
    if not version:
        return None
    return name, version


def parse_sysctl(text):
    """``net.mptcp.enabled = 1`` -> True; ``= 0`` -> False; anything else -> None."""
    for line in (text or "").splitlines():
        value = line.split("=", 1)[1].strip() if "=" in line else line.strip()
        if value == "1":
            return True
        if value == "0":
            return False
    return None


def split_address(token):
    """``[fd7a::1]:443`` -> ("fd7a::1", "443"); ``0.0.0.0:*`` -> ("0.0.0.0", "*")."""
    text = (token or "").strip()
    if text.startswith("["):
        close = text.find("]")
        if close == -1:
            return text, "*"
        port = text[close + 1:].lstrip(":") or "*"
        return text[1:close], port
    host, sep, port = text.rpartition(":")
    if not sep:
        return text, "*"
    return host or "*", port or "*"


def parse_ss(text):
    """``ss -Mln`` -> listeners, or None when the output is not an ss table.

    ``None`` matters: a kernel without MPTCP diagnostics, or an ``ss`` that does not
    understand ``-M``, produces something that is not a header -- and reporting that as
    "zero listeners" would read as "not on the path".
    """
    lines = [line for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return None
    header = lines[0].split()
    if not header or header[0] != "State":
        return None
    listeners = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 4 or parts[0] != "LISTEN":
            continue
        address, port = split_address(parts[3])
        scope, network = classify_address(address)
        listeners.append(Listener(address=address, port=port, scope=scope, network=network))
    return tuple(listeners)


def classify_address(address):
    """-> (scope, network-it-matched). The network is named so a label can be argued with.

    ``100.64.0.0/10`` is carrier-grade NAT, not a range Tailscale owns; on this host it
    is the Tailscale interface, so the scope is called ``tailnet`` but the matched
    prefix is printed alongside it rather than asserted.
    """
    text = (address or "").strip()
    if text in ALL_INTERFACES:
        return "all_interfaces", "0.0.0.0/0"
    try:
        ip = ipaddress.ip_address(text.split("%")[0])
    except ValueError:
        return "unknown", "unparsed"

    if ip.is_loopback:
        return "localhost", "127.0.0.0/8" if ip.version == 4 else "::1/128"
    if ip.version == 4:
        if ip in TAILNET_V4:
            return "tailnet", str(TAILNET_V4)
        for network in PRIVATE_V4:
            if ip in network:
                return "private_lan", str(network)
    else:
        if ip in TAILNET_V6:
            return "tailnet", str(TAILNET_V6)
        for network in PRIVATE_V6:
            if ip in network:
                return "private_lan", str(network)
    # Deliberately an allowlist of every non-public range above, with public as the
    # fallthrough. Accepting ipaddress.is_private here would relabel the documentation
    # ranges (TEST-NET-3, 203.0.113.0/24) as private LAN on Python versions that treat
    # them as private -- a classification that changes with the interpreter version is
    # not a measurement.
    return "public", "0.0.0.0/0"


def exposure_surface(listeners):
    """Unique scopes, widest first."""
    present = {listener.scope for listener in listeners}
    return tuple(scope for scope in SCOPE_ORDER if scope in present)


def parse_os_release(text):
    fields = {}
    for line in (text or "").splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return (
        fields.get("ID", "").lower(),
        fields.get("VERSION_ID", ""),
        fields.get("VERSION_CODENAME", ""),
    )


def _read_fixture(root, kind):
    name = FIXTURE_FILES[kind]
    path = os.path.join(root, name)
    if not os.path.isfile(path):
        return None, "%s: fixture %s missing" % (kind, path)
    try:
        with open(path, "r") as handle:
            return handle.read(), None
    except OSError as exc:
        return None, "%s: cannot read %s: %s" % (kind, path, exc)


def _run_probe(kind):
    command = COMMANDS[kind]
    try:
        proc = subprocess.run(command, capture_output=True, text=True,
                              timeout=PROBE_TIMEOUT, check=False)
    except FileNotFoundError:
        return None, "%s: command not found: %s" % (kind, command[0])
    except subprocess.TimeoutExpired:
        return None, "%s: %s timed out after %.0fs" % (kind, command[0], PROBE_TIMEOUT)
    except OSError as exc:
        return None, "%s: %s failed: %s" % (kind, command[0], exc)
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip().splitlines()
        return proc.stdout, "%s: %s exited %d%s" % (
            kind, command[0], proc.returncode, (": " + detail[0]) if detail else "")
    return proc.stdout, None


def probe(kind, fixtures=None):
    """One probe. Fixture mode reads a recorded transcript instead of running anything."""
    if fixtures:
        return _read_fixture(fixtures, kind)
    return _run_probe(kind)


def gather(fixtures=None):
    """Run every probe and assemble the facts. Errors are collected, never raised."""
    texts, errors = {}, []
    for kind in ("uname", "dpkg", "sysctl", "ss"):
        text, error = probe(kind, fixtures)
        texts[kind] = text
        if error:
            errors.append(error)

    if fixtures:
        os_text, os_error = _read_fixture(fixtures, "os_release")
        texts["os_release"] = os_text
        if os_error and os_error not in errors:
            errors.append(os_error)
    else:
        try:
            with open("/etc/os-release", "r") as handle:
                texts["os_release"] = handle.read()
        except OSError as exc:
            texts["os_release"] = None
            errors.append("os_release: cannot read /etc/os-release: %s" % exc)

    release = (texts["uname"] or "").strip().splitlines()
    release = release[0].strip() if release else None

    packages = parse_dpkg(texts["dpkg"]) if texts["dpkg"] is not None else {}
    package = package_for_release(packages, release)
    images = tuple(sorted(name for name, version in packages.items()
                          if version and name.startswith("linux-image-")
                          and "unsigned" not in name))

    enabled = parse_sysctl(texts["sysctl"]) if texts["sysctl"] is not None else None
    listeners = parse_ss(texts["ss"]) if texts["ss"] is not None else None
    distro, distro_release, codename = parse_os_release(texts["os_release"])

    return HostFacts(
        release=release,
        package_name=package[0] if package else None,
        package_version=package[1] if package else None,
        kernel_images=images,
        mptcp_enabled=enabled,
        mptcp_listeners=listeners,
        distro=distro,
        distro_release=distro_release,
        distro_codename=codename,
        errors=tuple(errors),
    )
