"""What this host is: its Ubuntu release and the kernel binaries installed on it.

Read-only and unprivileged. ``dpkg-query`` reports the source package for each binary, which
is what lets a row whose package is ``linux-hwe-6.8`` be matched to a binary named
``linux-image-6.8.0-40-generic`` without guessing from the name.
"""

import subprocess
from dataclasses import dataclass

from .verdict import InstalledPackage

OS_RELEASE = "/etc/os-release"
DPKG_ARGS = ["dpkg-query", "-W", "-f=${Package}\t${Version}\t${source:Package}\n",
             "linux-image-*"]


def source_family(source):
    """Map Ubuntu's signed/meta source packages onto the source tree the tracker names.

    ``dpkg-query`` reports the source of ``linux-image-7.0.0-38-generic`` as ``linux-signed``
    and of ``linux-image-generic`` as ``linux-meta``. The Ubuntu CVE tracker lists both under
    the ``linux`` source tree. Matching raw source names would silently ignore the kernel the
    host actually boots, which is the exact failure this tool exists to prevent.
    """
    text = (source or "").strip()
    for prefix, replacement in (("linux-signed", "linux"), ("linux-meta", "linux")):
        if text == prefix:
            return replacement
        if text.startswith(prefix + "-"):
            return replacement + text[len(prefix):]
    return text


@dataclass(frozen=True)
class HostFacts:
    release_id: str
    codename: str
    installed: tuple
    errors: tuple = ()

    @property
    def measured(self):
        return bool(self.release_id or self.codename)


def read_os_release(path=OS_RELEASE):
    """Parse os-release into a dict. A missing file yields an empty dict, not an exception."""
    values = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                key, separator, value = line.partition("=")
                if not separator:
                    continue
                values[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        return {}
    return values


def _query_kernels(runner, errors):
    try:
        result = runner(DPKG_ARGS, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as error:
        errors.append("dpkg-query failed: %s" % error)
        return []
    if result.returncode != 0:
        errors.append("dpkg-query exited %s: %s" % (result.returncode,
                                                    (result.stderr or "").strip()[:200]))
        return []
    installed = []
    for line in (result.stdout or "").splitlines():
        fields = line.split("\t")
        if len(fields) < 3:
            continue
        binary, version, source = fields[0].strip(), fields[1].strip(), fields[2].strip()
        if not binary.startswith("linux-image-") or not version or not source:
            continue
        installed.append(InstalledPackage(source=source_family(source), binary=binary,
                                          version=version))
    return installed


def facts(os_release_path=OS_RELEASE, runner=None):
    """Collect release id, codename and installed kernel binaries."""
    values = read_os_release(os_release_path)
    errors = []
    if not values:
        errors.append("could not read %s" % os_release_path)
    installed = _query_kernels(runner or subprocess.run, errors)
    return HostFacts(
        release_id=values.get("VERSION_ID", ""),
        codename=values.get("UBUNTU_CODENAME") or values.get("VERSION_CODENAME", ""),
        installed=tuple(installed),
        errors=tuple(errors),
    )
