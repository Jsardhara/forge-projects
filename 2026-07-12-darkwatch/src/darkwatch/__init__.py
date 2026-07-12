"""darkwatch public API."""
from __future__ import annotations

from .models import (
    ComplianceBand,
    Finding,
    Regulation,
    RegulationCheck,
    ScanResult,
    Severity,
)
from .rules import ALL_RULES, RULES_BY_ID, parse_html
from .scanner import band_for, regulation_checklist, scan_html
from .reporter import to_json, to_markdown, to_text

__all__ = [
    "ComplianceBand",
    "Finding",
    "Regulation",
    "RegulationCheck",
    "ScanResult",
    "Severity",
    "ALL_RULES",
    "RULES_BY_ID",
    "parse_html",
    "band_for",
    "regulation_checklist",
    "scan_html",
    "to_json",
    "to_markdown",
    "to_text",
]
