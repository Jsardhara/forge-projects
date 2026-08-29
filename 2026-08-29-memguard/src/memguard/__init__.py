"""memguard -- static scanner for AI-agent memory poisoning & prompt-injection."""
from .models import Finding, ScanResult, Severity, Verdict
from .rules import scan_text
from .scanner import aggregate_score, aggregate_verdict, collect_files, scan_paths

__version__ = "0.1.0"
__all__ = [
    "Finding", "ScanResult", "Severity", "Verdict",
    "aggregate_score", "aggregate_verdict", "collect_files", "scan_paths", "scan_text",
]