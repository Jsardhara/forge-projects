"""Risk scoring and banding for mcpshield findings."""
from __future__ import annotations

from typing import Iterable

from mcpshield.models import SEVERITY_WEIGHT, Finding

# Band thresholds.
FAIL_IF_CRITICAL = True
FAIL_RISK_AT = 50  # risk_score >= this => FAIL
WARN_RISK_AT = 20  # risk_score >= this (but < FAIL) => WARN
WARN_IF_HIGH = True  # any HIGH (without CRITICAL) => at least WARN


def score_findings(findings: Iterable[Finding]) -> tuple[int, str]:
    """Return (risk_score 0-100, band PASS|WARN|FAIL)."""
    findings = list(findings)
    raw = sum(SEVERITY_WEIGHT.get(f.severity, 0) for f in findings)
    risk_score = min(100, raw)

    has_critical = any(f.severity == "CRITICAL" for f in findings)
    has_high = any(f.severity == "HIGH" for f in findings)

    if (FAIL_IF_CRITICAL and has_critical) or risk_score >= FAIL_RISK_AT:
        return risk_score, "FAIL"
    if (WARN_IF_HIGH and has_high) or risk_score >= WARN_RISK_AT:
        return risk_score, "WARN"
    return risk_score, "PASS"
