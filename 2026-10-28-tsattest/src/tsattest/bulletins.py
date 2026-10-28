"""The bulletin table and the applicability rules.

The vendor publishes roughly one bulletin a week, so a hand-written table of
``(bulletin, fixed_in)`` is the correct data structure here. Version comparison
is never against "latest": a host can be past one fix and short of the next.

Applicability is the part a CVE feed cannot give you. Three bulletins only
matter when a feature is switched on, and the applicability input is often
something we cannot read (``None``), which must never be flattened into
"does not apply".
"""

from . import semver

OPEN = "OPEN"
CLOSED = "CLOSED"
NOT_APPLICABLE = "NOT_APPLICABLE"
UNKNOWN = "UNKNOWN"

APPLY_ALWAYS = "always"
APPLY_SSH = "ssh"
APPLY_SERVE = "serve"
APPLY_SERVE_UNIX = "serve_unix_backend"
APPLY_SERVE_MULTI = "serve_multi_mount_tls"

_VERDICT_RANK = {OPEN: 3, UNKNOWN: 2, NOT_APPLICABLE: 1, CLOSED: 0}


class Bulletin(object):
    __slots__ = ("key", "title", "fixed_in", "applicability")

    def __init__(self, key, title, fixed_in, applicability):
        self.key = key
        self.title = title
        self.fixed_in = fixed_in
        self.applicability = applicability


BULLETINS = (
    Bulletin("TS-2026-013",
             "eight compromised eMudhra TLS intermediates trusted by the system store",
             "1.104.2", APPLY_ALWAYS),
    Bulletin("TS-2026-014",
             "Tailscale SSH unix-socket forwarding validated lexically but dialed as root "
             "(and ssh -R could unlink root-owned sockets)",
             "1.104.4", APPLY_SSH),
    Bulletin("TS-2026-015",
             "embedded SSH server leaked memory on window-change/env appends, allocations "
             "persist after disconnect",
             "1.104.4", APPLY_SSH),
    Bulletin("TS-2026-016",
             "tailscale serve unix backends dialed as root; symlink guard only ran at config reload",
             "1.104.4", APPLY_SERVE_UNIX),
    Bulletin("TS-2026-017",
             "HTTP/2 serve context raced on AppCapabilities across mounts (capability bleed)",
             "1.104.4", APPLY_SERVE_MULTI),
)


class Facts(object):
    """What the probes managed to establish. ``None`` means unmeasurable, not false."""

    __slots__ = ("version", "ssh_enabled", "serve_present", "serve_unix_backend",
                 "serve_mounts", "serve_tls")

    def __init__(self, version=None, ssh_enabled=None, serve_present=None,
                 serve_unix_backend=None, serve_mounts=None, serve_tls=None):
        self.version = version
        self.ssh_enabled = ssh_enabled
        self.serve_present = serve_present
        self.serve_unix_backend = serve_unix_backend
        self.serve_mounts = serve_mounts
        self.serve_tls = serve_tls


class Result(object):
    __slots__ = ("key", "title", "fixed_in", "status", "detail")

    def __init__(self, key, title, fixed_in, status, detail):
        self.key = key
        self.title = title
        self.fixed_in = fixed_in
        self.status = status
        self.detail = detail

    def as_dict(self):
        return {"key": self.key, "title": self.title, "fixed_in": self.fixed_in,
                "status": self.status, "detail": self.detail}


def _applicability(bulletin, facts):
    """Return (applies, reason). ``applies`` is None when it cannot be decided."""
    rule = bulletin.applicability
    if rule == APPLY_ALWAYS:
        return True, "applies to every node"
    if rule == APPLY_SSH:
        if facts.ssh_enabled is None:
            return None, ("Tailscale SSH state could not be read "
                          "(`tailscale debug prefs` -> RunSSH)")
        if facts.ssh_enabled:
            return True, "Tailscale SSH is enabled (debug prefs RunSSH=true)"
        return False, "Tailscale SSH is disabled (debug prefs RunSSH=false)"
    if rule == APPLY_SERVE:
        if facts.serve_present is None:
            return None, "serve configuration could not be read (`tailscale serve status`)"
        if facts.serve_present:
            return True, "a serve configuration is present"
        return False, "no serve configuration"
    if rule == APPLY_SERVE_UNIX:
        if facts.serve_present is None or facts.serve_unix_backend is None:
            return None, "serve backends could not be read (`tailscale serve status`)"
        if not facts.serve_present:
            return False, "no serve configuration, so no serve backend of any kind"
        if facts.serve_unix_backend:
            return True, "serve has a unix-socket backend"
        return False, "serve backends are all proxied TCP, no unix socket"
    if rule == APPLY_SERVE_MULTI:
        # The advisory names two conditions: serve TLS enabled, and at least two
        # mounts with different capability requirements on the same node.
        if facts.serve_present is None:
            return None, "serve configuration could not be read (`tailscale serve status`)"
        if not facts.serve_present:
            return False, "no serve configuration"
        if facts.serve_mounts is None or facts.serve_tls is None:
            return None, ("serve mounts could not be counted (`tailscale serve status` "
                          "gave output that could not be parsed)")
        if not facts.serve_tls:
            return False, "serve is not TLS-enabled"
        if facts.serve_mounts < 2:
            return False, ("serve has %d mount, and the advisory needs at least two "
                           "mounts with different capability requirements"
                           % facts.serve_mounts)
        return True, ("serve has %d mounts over TLS; the advisory needs at least two "
                      "with different capability requirements" % facts.serve_mounts)
    raise ValueError("unknown applicability rule: %r" % (rule,))


def evaluate(facts):
    """Evaluate every bulletin against the facts. Returns a list of Result."""
    results = []
    for bulletin in BULLETINS:
        if facts.version is None:
            results.append(Result(
                bulletin.key, bulletin.title, bulletin.fixed_in, UNKNOWN,
                "tailscale version could not be read, so the fixed-in comparison "
                "cannot be made"))
            continue
        applies, reason = _applicability(bulletin, facts)
        if applies is None:
            results.append(Result(bulletin.key, bulletin.title, bulletin.fixed_in,
                                  UNKNOWN, reason))
        elif not applies:
            results.append(Result(bulletin.key, bulletin.title, bulletin.fixed_in,
                                  NOT_APPLICABLE, reason))
        elif facts.version >= semver.parse(bulletin.fixed_in):
            results.append(Result(bulletin.key, bulletin.title, bulletin.fixed_in,
                                  CLOSED, "running %s, fixed in %s"
                                  % (facts.version, bulletin.fixed_in)))
        else:
            results.append(Result(bulletin.key, bulletin.title, bulletin.fixed_in,
                                  OPEN, "running %s, fixed in %s; %s"
                                  % (facts.version, bulletin.fixed_in, reason)))
    return results


def verdict(results):
    """Severity-dominant: an OPEN bulletin outranks UNKNOWN outranks everything."""
    worst = max((_VERDICT_RANK[r.status] for r in results), default=0)
    if worst == _VERDICT_RANK[OPEN]:
        return "FAIL"
    if worst == _VERDICT_RANK[UNKNOWN]:
        return "UNKNOWN"
    return "PASS"


def exit_code(name):
    """0 = nothing at threshold, 1 = at/above, 2 = could not answer."""
    return {"PASS": 0, "FAIL": 1, "UNKNOWN": 2}[name]
