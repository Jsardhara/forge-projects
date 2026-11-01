"""kcheck -- is THIS host's kernel in a known kernel CVE's affected range?

Read-only. Offline. Stdlib only. No root, no network, no package manager.
"""
__version__ = "0.1.0"

from .assess import Finding, assess_cve, exit_code  # noqa: F401
