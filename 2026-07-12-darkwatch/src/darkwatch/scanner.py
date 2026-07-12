"""Scan orchestration: run rules, compute band, build per-regulation checklist."""
from __future__ import annotations

from typing import List

from .models import (
    ComplianceBand,
    Finding,
    Regulation,
    RegulationCheck,
    ScanResult,
    Severity,
)
from .rules import ALL_RULES, parse_html

# Banding thresholds: >=1 critical OR >=3 findings total = NON_COMPLIANT;
# otherwise any finding = NEEDS_REVIEW; none = COMPLIANT.
NON_COMPLIANT_CRITICAL_MIN = 1
NON_COMPLIANT_TOTAL_MIN = 3


def band_for(findings: List[Finding]) -> ComplianceBand:
    if not findings:
        return ComplianceBand.COMPLIANT
    critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
    if critical >= NON_COMPLIANT_CRITICAL_MIN or len(findings) >= NON_COMPLIANT_TOTAL_MIN:
        return ComplianceBand.NON_COMPLIANT
    return ComplianceBand.NEEDS_REVIEW


def scan_html(html: str, url: str = "unknown") -> ScanResult:
    ctx = parse_html(html)
    findings: List[Finding] = []
    for rule in ALL_RULES:
        f = rule.scan(ctx, url)
        if f is not None:
            findings.append(f)
    band = band_for(findings)
    return ScanResult(url=url, findings=findings, band=band)


def regulation_checklist(html: str, url: str = "unknown") -> List[RegulationCheck]:
    result = scan_html(html, url)
    regs = set(f.regulation for f in result.findings)
    checks: List[RegulationCheck] = []
    for reg in Regulation:
        reg_findings = [f for f in result.findings if f.regulation == reg]
        crit = sum(1 for f in reg_findings if f.severity == Severity.CRITICAL)
        high = sum(1 for f in reg_findings if f.severity == Severity.HIGH)
        if not reg_findings:
            status = "pass"
            note = "No heuristics triggered for this regulation."
        elif crit >= 1 or high >= 1 or len(reg_findings) >= 3:
            status = "fail"
            note = "Material dark-pattern(s) detected under this regulation."
        else:
            status = "warn"
            note = "Non-critical issues detected; manual review recommended."
        checks.append(
            RegulationCheck(
                regulation=reg,
                status=status,
                findings=len(reg_findings),
                critical=crit,
                note=note,
            )
        )
    return checks
