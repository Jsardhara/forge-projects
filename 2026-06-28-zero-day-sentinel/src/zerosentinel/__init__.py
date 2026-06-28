"""ZeroDaySentinel — GitHub 0-Day Vulnerability Detection & Patch Automation."""

__version__ = "0.1.0"

from zerosentinel.models import (
    VulnerabilityFingerprint,
    ExploitRepositry,
    DetectionResult,
    Severity,
    PatchSuggestion,
)
from zerosentinel.scanner import ZeroDayScanner
from zerosentinel.matcher import DependencyMatcher
from zerosentinel.patchgen import PatchGenerator
from zerosentinel.reporter import ReportGenerator

__all__ = [
    "ZeroDayScanner",
    "DependencyMatcher",
    "PatchGenerator",
    "ReportGenerator",
    "VulnerabilityFingerprint",
    "ExploitRepositry",
    "DetectionResult",
    "PatchSuggestion",
    "Severity",
]
