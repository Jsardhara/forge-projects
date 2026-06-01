"""AI Leak Scanner — Vulnerability database and scanner models."""

from .vulndb import (
    Vulnerability,
    Severity,
    AttackVector,
    VULNERABILITIES,
    get_vulnerability,
    get_by_vendor,
    get_by_severity,
    get_unpatched,
    get_attack_vectors,
)
from .scanner import ScanFinding, ScanReport, scan_extensions, scan_all, get_risk_level

__version__ = "0.1.0"
__all__ = [
    "Vulnerability",
    "Severity",
    "AttackVector",
    "VULNERABILITIES",
    "get_vulnerability",
    "get_by_vendor",
    "get_by_severity",
    "get_unpatched",
    "get_attack_vectors",
    "ScanFinding",
    "ScanReport",
    "scan_extensions",
    "scan_all",
    "get_risk_level",
]
