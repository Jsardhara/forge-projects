"""Report renderers: text, markdown, JSON."""
from __future__ import annotations

from typing import List

from .models import ComplianceBand, Finding, Regulation, RegulationCheck, ScanResult, Severity
from .scanner import regulation_checklist

_BAND_LABEL = {
    ComplianceBand.COMPLIANT: "COMPLIANT",
    ComplianceBand.NEEDS_REVIEW: "NEEDS REVIEW",
    ComplianceBand.NON_COMPLIANT: "NON-COMPLIANT",
}

_SEV_ICON = {
    Severity.CRITICAL: "!!",
    Severity.HIGH: "!!",
    Severity.MEDIUM: "##",
    Severity.LOW: "..",
}


def _ordered(findings: List[Finding]) -> List[Finding]:
    return sorted(findings, key=lambda f: (f.severity.weight * -1, f.rule_id))


def _checklist_for(result: ScanResult) -> List[RegulationCheck]:
    """Build the per-regulation checklist from an already-scanned result."""
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


def to_json(result: ScanResult) -> str:
    import json

    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


def to_text(result: ScanResult) -> str:
    lines = []
    lines.append("=" * 64)
    lines.append("darkwatch — Dark-Pattern Compliance Scan")
    lines.append("=" * 64)
    lines.append(f"URL:     {result.url}")
    lines.append(f"Band:    {_BAND_LABEL[result.band]}  ({result.band.value})")
    lines.append(f"Scanned: {result.scanned_at.isoformat()}")
    s = result.summary()
    lines.append(
        f"Findings: {s['total']}  "
        f"[critical={s['by_severity']['critical']} high={s['by_severity']['high']} "
        f"medium={s['by_severity']['medium']} low={s['by_severity']['low']}]"
    )
    lines.append("-" * 64)
    if not result.findings:
        lines.append("No dark-pattern heuristics triggered. Clean.")
    else:
        for f in _ordered(result.findings):
            lines.append(f"[{_SEV_ICON[f.severity]}] {f.severity.value.upper()}  {f.title}")
            lines.append(f"     rule:     {f.rule_id}")
            lines.append(f"     regulation: {f.regulation.value}")
            lines.append(f"     evidence: {f.evidence}")
            lines.append("")
    lines.append("=" * 64)
    return "\n".join(lines)


def to_markdown(result: ScanResult) -> str:
    lines = []
    lines.append(f"# darkwatch compliance report — `{result.url}`")
    lines.append("")
    lines.append(f"**Band:** {_BAND_LABEL[result.band]}")
    lines.append("")
    s = result.summary()
    lines.append(
        f"**Findings:** {s['total']} "
        f"(critical {s['by_severity']['critical']}, high {s['by_severity']['high']}, "
        f"medium {s['by_severity']['medium']}, low {s['by_severity']['low']})"
    )
    lines.append("")
    if result.findings:
        lines.append("## Findings")
        lines.append("")
        lines.append("| Severity | Rule | Regulation | Evidence |")
        lines.append("| --- | --- | --- | --- |")
        for f in _ordered(result.findings):
            ev = f.evidence.replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| {f.severity.value} | `{f.rule_id}` | {f.regulation.value} | {ev} |"
            )
        lines.append("")
    lines.append("## Regulation checklist")
    lines.append("")
    lines.append("| Regulation | Status | Findings | Critical |")
    lines.append("| --- | --- | --- | --- |")
    for c in _checklist_for(result):
        lines.append(
            f"| {c.regulation.value} | {c.status} | {c.findings} | {c.critical} |"
        )
    lines.append("")
    return "\n".join(lines)
