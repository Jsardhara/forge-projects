"""plugattest -- declared-vs-detected capability attestation for plugin/skill packages."""

from .attest import EXIT_CLEAN, EXIT_FINDINGS, EXIT_USAGE, attest
from .manifest import Declared, load_declared, normalize_capability
from .models import Finding, Report, Severity
from .scanner import CapabilityHit, scan_package

__version__ = "1.0.0"

__all__ = [
    "attest",
    "load_declared",
    "scan_package",
    "normalize_capability",
    "Declared",
    "Finding",
    "Report",
    "Severity",
    "CapabilityHit",
    "EXIT_CLEAN",
    "EXIT_FINDINGS",
    "EXIT_USAGE",
]
