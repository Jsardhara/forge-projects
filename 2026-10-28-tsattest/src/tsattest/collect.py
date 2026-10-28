"""Read every surface the verdict depends on, and remember which ones refused.

Three states, never two:

* ``MEASURED``   -- the value came back from the surface that owns it
* ``UNREADABLE`` -- the surface exists but we were refused (EACCES, no binary)
* ``ABSENT``     -- the surface answered, and the answer was "nothing configured"

An unreadable value is never rendered as a negative finding, and a value
declared in a config file is never rendered as a value the process is
carrying. That collapse is the whole bug this tool exists to avoid.
"""

import json
import os
import platform
import subprocess

from . import semver
from .bulletins import Facts

MEASURED = "measured"
UNREADABLE = "unreadable"
ABSENT = "absent"

CONSISTENT = "CONSISTENT"
DISAGREE = "DISAGREE"
UNKNOWN = "UNKNOWN"

MITIGATION_VAR = "TS_SSH_DISABLE_FORWARDING"
DEFAULT_FILE = "/etc/default/tailscaled"
PROC_ENVIRON = "/proc/%s/environ"

_FIXTURE_FILES = {
    "version": "version.txt",
    "prefs": "prefs.json",
    "status": "status.json",
    "serve": "serve.txt",
    "env": "environ.txt",
    "defaults": "defaults.txt",
}


class Probe(object):
    __slots__ = ("name", "source", "status", "value", "reason")

    def __init__(self, name, source, status, value=None, reason=None):
        self.name = name
        self.source = source
        self.status = status
        self.value = value
        self.reason = reason

    def as_dict(self):
        return {"name": self.name, "source": self.source, "status": self.status,
                "reason": self.reason}


class Surface(object):
    """One value, its provenance and whether it was actually readable."""

    __slots__ = ("value", "status", "source", "reason")

    def __init__(self, value, status, source, reason=None):
        self.value = value
        self.status = status
        self.source = source
        self.reason = reason

    def as_dict(self):
        return {"value": self.value, "status": self.status, "source": self.source,
                "reason": self.reason}


class Mitigation(object):
    __slots__ = ("declared", "actual", "consistency", "advice")

    def __init__(self, declared, actual, consistency, advice):
        self.declared = declared
        self.actual = actual
        self.consistency = consistency
        self.advice = advice

    def as_dict(self):
        return {"declared": self.declared.as_dict(), "actual": self.actual.as_dict(),
                "consistency": self.consistency, "advice": self.advice}


class Collected(object):
    __slots__ = ("facts", "probes", "notes", "ssh_source", "ssh_host_keys_present",
                 "mitigation", "version_raw", "node", "backend_state")

    def __init__(self, **kwargs):
        for slot in self.__slots__:
            setattr(self, slot, kwargs.get(slot))

    def probe(self, name):
        for item in self.probes or ():
            if item.name == name:
                return item
        raise KeyError(name)

    def probe_count(self):
        return len(self.probes or ())

    def measured_count(self):
        return sum(1 for p in self.probes or () if p.status == MEASURED)

    def unmeasurable_count(self):
        return sum(1 for p in self.probes or () if p.status != MEASURED)

    def facts_obj(self):
        return self.facts


def parse_environ(text):
    """Parse a NUL-separated /proc/<pid>/environ blob. Malformed entries are skipped."""
    out = {}
    for chunk in (text or "").split("\x00"):
        if "=" not in chunk:
            continue
        key, _, value = chunk.partition("=")
        if key:
            out[key] = value
    return out


def _run(command):
    """Run a command. Returns (ok, stdout, stderr). Never raises for a missing binary."""
    try:
        proc = subprocess.run(command, capture_output=True, text=True,
                              timeout=15, check=False)
    except FileNotFoundError as exc:
        return False, "", "cannot execute %s: %s" % (" ".join(command), exc)
    except OSError as exc:
        return False, "", "cannot execute %s: %s" % (" ".join(command), exc)
    except subprocess.TimeoutExpired:
        return False, "", "timed out: %s" % (" ".join(command),)
    if proc.returncode != 0:
        return False, proc.stdout or "", proc.stderr or "exit %d" % proc.returncode
    return True, proc.stdout or "", proc.stderr or ""


def _read_file(path):
    try:
        with open(path, "r", errors="replace") as handle:
            return True, handle.read()
    except OSError as exc:
        return False, str(exc)


def _source(fixtures, name, live_desc):
    """Where a probe reads from, for both display and fixture mode."""
    if fixtures:
        return os.path.join(fixtures, _FIXTURE_FILES[name])
    return live_desc


def _fixture_text(fixtures, name):
    """In fixture mode, read the file that stands in for a surface.

    A file that is *missing* from an existing fixture directory models a probe
    that could not be read -- not one whose answer was "nothing configured".
    """
    path = os.path.join(fixtures, _FIXTURE_FILES[name])
    ok, text = _read_file(path)
    if ok:
        return True, text, None
    return False, "", "cannot read fixture %s (%s)" % (path, text)


def _probe_version(fixtures, tailscale_bin):
    source = _source(fixtures, "version", "%s version" % tailscale_bin)
    if fixtures:
        ok, text, why = _fixture_text(fixtures, "version")
        if not ok:
            return None, Probe("version", source, UNREADABLE, None, why)
    else:
        ok, text, why = _run([tailscale_bin, "version"])
        if not ok:
            return None, Probe("version", source, UNREADABLE, None, why)
    raw = semver.first_line(text)
    try:
        version = semver.parse(raw)
    except ValueError:
        return None, Probe("version", source, UNREADABLE, None,
                           "could not parse a version from %r (expected e.g. "
                           "1.102.3 or 1.102.3-t<build>)" % raw)
    return version, Probe("version", source, MEASURED, str(version))


def _probe_prefs(fixtures, tailscale_bin):
    source = _source(fixtures, "prefs", "%s debug prefs" % tailscale_bin)
    if fixtures:
        ok, text, why = _fixture_text(fixtures, "prefs")
    else:
        ok, text, why = _run([tailscale_bin, "debug", "prefs"])
    if not ok:
        return None, Probe("prefs", source, UNREADABLE, None, why)
    try:
        prefs = json.loads(text)
    except ValueError as exc:
        return None, Probe("prefs", source, UNREADABLE, None,
                           "could not parse JSON from %s: %s" % (source, exc))
    if not isinstance(prefs, dict) or "RunSSH" not in prefs:
        return None, Probe("prefs", source, UNREADABLE, None,
                           "%s returned no RunSSH field" % source)
    return dict(prefs), Probe("prefs", source, MEASURED, {"RunSSH": prefs["RunSSH"]})


def _probe_status(fixtures, tailscale_bin):
    source = _source(fixtures, "status", "%s status --json" % tailscale_bin)
    if fixtures:
        ok, text, why = _fixture_text(fixtures, "status")
    else:
        ok, text, why = _run([tailscale_bin, "status", "--json"])
    if not ok:
        return None, Probe("status", source, UNREADABLE, None, why)
    try:
        doc = json.loads(text)
    except ValueError as exc:
        return None, Probe("status", source, UNREADABLE, None,
                           "could not parse JSON from %s: %s" % (source, exc))
    if not isinstance(doc, dict):
        return None, Probe("status", source, UNREADABLE, None,
                           "%s did not return an object" % source)
    return doc, Probe("status", source, MEASURED, {
        "BackendState": doc.get("BackendState"),
        "peers": len(doc.get("Peer") or {}),
        "ssh_host_keys_present": _ssh_host_keys_present(doc),
    })


def _ssh_host_keys_present(doc):
    """True only if the status document actually carries usable host keys."""
    self_node = doc.get("Self") or {}
    keys = self_node.get("SSH_HostKeys")
    return bool(keys)


def parse_serve(text):
    """Read the shape of a `tailscale serve status` table.

    The table lists one ``|-- <mount> <mode> <backend>`` line per mount, under a
    ``https://`` (TLS) or ``http://`` header. Mount count and TLS state are what
    two of the advisories' applicability conditions actually turn on.
    """
    body = (text or "").strip()
    if not body or "no serve config" in body.lower():
        return None
    mounts = [line for line in body.splitlines() if line.strip().startswith("|--")]
    header = body.splitlines()[0].strip().lower()
    return {
        "present": True,
        "mounts": len(mounts),
        "tls": header.startswith("https://"),
        "unix_backend": "unix:" in body,
    }


def _probe_serve(fixtures, tailscale_bin):
    source = _source(fixtures, "serve", "%s serve status" % tailscale_bin)
    if fixtures:
        ok, text, why = _fixture_text(fixtures, "serve")
        if not ok:
            return None, Probe("serve", source, UNREADABLE, None, why)
    else:
        ok, text, why = _run([tailscale_bin, "serve", "status"])
        if not ok:
            if "no serve config" in (why or "").lower():
                return None, Probe("serve", source, ABSENT, False, "no serve config")
            return None, Probe("serve", source, UNREADABLE, None, why)
    shaped = parse_serve(text)
    if shaped is None:
        return None, Probe("serve", source, ABSENT, False, "no serve config")
    return shaped, Probe("serve", source, MEASURED, shaped)


def _tailscaled_pid(fixtures):
    if fixtures:
        return None
    ok, out, _ = _run(["pgrep", "-x", "tailscaled"])
    if not ok:
        return None
    first = semver.first_line(out)
    return first or None


def _probe_env(fixtures):
    """The running process's environment. Root-only on a real install."""
    if fixtures:
        source = _source(fixtures, "env", PROC_ENVIRON % "<pid>")
        ok, text, why = _fixture_text(fixtures, "env")
        if not ok:
            why = ("%s; the running process environment is readable only by root, so "
                   "the loaded value of %s is UNKNOWN (needs root)"
                   % (why, MITIGATION_VAR))
    else:
        pid = _tailscaled_pid(None)
        if pid is None:
            return None, Probe("env", "/proc/<pid>/environ", UNREADABLE, None,
                               "cannot find the tailscaled pid (pgrep -x tailscaled); "
                               "the running process cannot be measured")
        source = PROC_ENVIRON % pid
        ok, text = _read_file(source)
        why = ("permission denied reading %s: env unreadable (needs root), so the "
               "loaded value of %s is UNKNOWN -- run as root to measure it"
               % (source, MITIGATION_VAR)) if not ok else None
    if not ok:
        return None, Probe("env", source, UNREADABLE, None, why)
    env = parse_environ(text)
    value = env.get(MITIGATION_VAR, "")
    return env, Probe("env", source, MEASURED, {MITIGATION_VAR: value})


def _probe_defaults(fixtures, defaults_file):
    source = _source(fixtures, "defaults", defaults_file)
    if fixtures:
        ok, text, why = _fixture_text(fixtures, "defaults")
        if not ok:
            return None, Probe("defaults", source, UNREADABLE, None, why)
    else:
        ok, text = _read_file(defaults_file)
        if not ok:
            return None, Probe("defaults", source, UNREADABLE, None,
                               "cannot read %s (%s)" % (defaults_file, text))
    return parse_shell_vars(text), Probe("defaults", source, MEASURED, None)


def parse_shell_vars(text):
    """Parse KEY=value lines from a systemd EnvironmentFile. Comments ignored."""
    out = {}
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def _mitigation(defaults_vars, env_vars, defaults_probe, env_probe):
    declared_source = defaults_probe.source
    actual_source = env_probe.source
    if defaults_probe.status != MEASURED:
        declared = Surface(None, UNREADABLE, declared_source, defaults_probe.reason)
    else:
        declared = Surface(defaults_vars.get(MITIGATION_VAR, ""), MEASURED,
                           declared_source)
    if env_probe.status != MEASURED:
        actual = Surface(None, UNREADABLE, actual_source, env_probe.reason)
    else:
        actual = Surface(env_vars.get(MITIGATION_VAR, ""), MEASURED, actual_source)

    if actual.status != MEASURED:
        consistency = UNKNOWN
        advice = ("actual value is unmeasurable: %s is only authoritative in the "
                  "running tailscaled process, and that read needs root. Re-run as "
                  "root (sudo tsattest) to measure it. Declared file value %r is NOT "
                  "evidence the mitigation is loaded."
                  % (MITIGATION_VAR, declared.value))
    elif declared.status != MEASURED:
        consistency = CONSISTENT
        advice = ("no readable declaration (checked %s); the running process value %r "
                  "is what counts" % (declared_source, actual.value))
    elif declared.value == actual.value:
        consistency = CONSISTENT
        advice = ("declared and loaded agree (%s=%r)" % (MITIGATION_VAR, actual.value)
                  if actual.value else
                  "no mitigation declared and none loaded: docs point at a client "
                  "upgrade to 1.104.4")
    else:
        consistency = DISAGREE
        advice = ("declaration != reality: %s declares %r but the running process "
                  "carries %r. The process is the one that matters; fix %s to match "
                  "intent, then restart tailscaled."
                  % (declared_source, declared.value, actual.value, declared_source))
    return Mitigation(declared, actual, consistency, advice)


def _status_notes(status_doc, ssh_host_keys_present, ssh_enabled, version):
    notes = []
    if ssh_enabled is True and ssh_host_keys_present is False:
        notes.append(
            "surface contradiction: `tailscale status --json` reports "
            "Self.SSH_HostKeys=null while `tailscale debug prefs` reports "
            "RunSSH=true. The status field is NOT used to decide SSH state; reading "
            "it would report this host as SSH-off, a false negative in the unsafe "
            "direction.")
    if not status_doc:
        notes.append("`tailscale status --json` was not readable: peer count and "
                     "BackendState are unknown.")
        return notes
    backend = status_doc.get("BackendState")
    if backend and backend != "Running":
        notes.append("BackendState is %r, not 'Running': the node is not on the tailnet "
                     "right now." % backend)
    status_version = status_doc.get("ClientVersion") or status_doc.get("Version")
    if version is not None and status_version:
        try:
            if semver.parse(status_version) != version:
                notes.append("version surface disagreement: `tailscale version` says %s "
                             "while `status --json` says %s." % (version, status_version))
        except ValueError:
            notes.append("`status --json` reported an unparseable ClientVersion %r."
                         % (status_version,))
    return notes


def gather(fixtures=None, tailscale_bin="tailscale", defaults_file=DEFAULT_FILE):
    """Collect every surface and assemble the Facts plus full probe accounting."""
    version, version_probe = _probe_version(fixtures, tailscale_bin)
    prefs, prefs_probe = _probe_prefs(fixtures, tailscale_bin)
    status_doc, status_probe = _probe_status(fixtures, tailscale_bin)
    serve_shape, serve_probe = _probe_serve(fixtures, tailscale_bin)
    env_vars, env_probe = _probe_env(fixtures)
    defaults_vars, defaults_probe = _probe_defaults(fixtures, defaults_file)

    ssh_enabled = None
    if prefs is not None:
        ssh_enabled = bool(prefs.get("RunSSH"))

    ssh_host_keys_present = None
    serve_present = None
    serve_unix_backend = None
    serve_mounts = None
    serve_tls = None
    if status_probe.status == MEASURED:
        ssh_host_keys_present = status_probe.value.get("ssh_host_keys_present")
    if serve_probe.status == MEASURED and serve_shape:
        serve_present = True
        serve_unix_backend = bool(serve_shape.get("unix_backend"))
        serve_mounts = serve_shape.get("mounts")
        serve_tls = serve_shape.get("tls")
    elif serve_probe.status == ABSENT:
        serve_present = False
        serve_unix_backend = False
        serve_mounts = 0
        serve_tls = False

    facts = Facts(version=version, ssh_enabled=ssh_enabled,
                  serve_present=serve_present, serve_unix_backend=serve_unix_backend,
                  serve_mounts=serve_mounts, serve_tls=serve_tls)

    mitigation = _mitigation(defaults_vars or {}, env_vars or {},
                             defaults_probe, env_probe)
    notes = _status_notes(status_doc, ssh_host_keys_present, ssh_enabled, version)

    return Collected(
        facts=facts,
        probes=[version_probe, prefs_probe, status_probe, serve_probe, env_probe,
                defaults_probe],
        notes=notes,
        ssh_source="tailscale debug prefs",
        ssh_host_keys_present=ssh_host_keys_present,
        mitigation=mitigation,
        version_raw=str(version) if version else None,
        node=((status_doc or {}).get("Self") or {}).get("HostName") or platform.node(),
        backend_state=(status_doc or {}).get("BackendState"),
    )
