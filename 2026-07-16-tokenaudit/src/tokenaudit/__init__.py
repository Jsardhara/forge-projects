"""tokenaudit -- coding-agent token-cost profiler & efficiency auditor.

Diagnose where tokens go in agent session transcripts (pre-read overhead, redundant
file reads, telemetry bloat) and get concrete savings recommendations.
"""
from __future__ import annotations

from .audit import recommendations
from .models import (
    CostReport,
    FileRead,
    Message,
    PhaseBreakdown,
    Session,
    Usage,
    WasteFinding,
    Recommendation,
)
from .parse import parse_session, parse_session_text
from .pricing import DEFAULT_PRICING, cost_for, load_prices
from .profile import file_reads, phase_breakdown, waste_findings
from .report import build_report

__all__ = [
    "CostReport",
    "FileRead",
    "Message",
    "PhaseBreakdown",
    "Session",
    "Usage",
    "WasteFinding",
    "Recommendation",
    "parse_session",
    "parse_session_text",
    "DEFAULT_PRICING",
    "cost_for",
    "load_prices",
    "file_reads",
    "phase_breakdown",
    "waste_findings",
    "build_report",
    "recommendations",
    "run_cli",
]
