"""cvewatch - watch a Ubuntu CVE until this host leaves its affected range.

Read-only, keyless, standard library only. One GET to one allowlisted host per CVE, a real
dpkg version comparison against the installed kernels, and a diff against the previous run
so the only thing that ever alerts is a transition.
"""

__version__ = "1.0.0"
__all__ = ["version", "tracker", "verdict", "state", "fetch", "host"]
