"""Report formatting for aidisclose (markdown + JSON)."""
from __future__ import annotations

from typing import Optional

from .engine import ComplianceReport


def to_markdown(report: ComplianceReport) -> str:
    lines: list = []
    lines.append(f"# AI-Disclosure Compliance Report: {report.profile_name}")
    lines.append("")
    lines.append(f"- **Reference date:** {report.reference_date.isoformat()}")
    lines.append(f"- **Overall gap score:** {report.score:.1f} / 100")
    lines.append(f"- **Risk band:** {report.band}")
    lines.append(
        f"- **Blocking gaps:** {'YES' if report.blocking else 'none'}"
    )
    lines.append(
        f"- **Applicable in-force mandates:** {len(report.applicable)}"
    )
    lines.append(f"- **Monitored (proposed/upcoming):** {len(report.monitored)}")
    lines.append("")

    if report.applicable:
        lines.append("## Applicable mandates & gaps")
        lines.append("")
        for am in report.applicable:
            m = am.mandate
            lines.append(f"### {m.title} ({m.jurisdiction})")
            lines.append(f"- Status: {m.status.value} | Effective: "
                         f"{m.effective_date.isoformat() if m.effective_date else 'n/a'}")
            lines.append(f"- Gap: {am.gap_weight}/{am.total_weight} obligation-weight "
                         f"({am.ratio * 100:.0f}% non-compliant)")
            if am.unmet:
                lines.append("- **Unmet obligations:**")
                for o in am.unmet:
                    lines.append(f"  - [{o.severity.value.upper()}] {o.label}")
            else:
                lines.append("- All obligations satisfied.")
            lines.append(f"- Source: {m.source}")
            lines.append("")

    if report.monitored:
        lines.append("## Monitored (not yet enforceable)")
        lines.append("")
        for m in report.monitored:
            lines.append(f"- **{m.title}** ({m.jurisdiction}, {m.status.value})")
            lines.append(f"  - {m.summary}")
            lines.append(f"  - Source: {m.source}")
            lines.append("")

    if not report.applicable and not report.monitored:
        lines.append("_No applicable mandates for this profile._")
        lines.append("")

    return "\n".join(lines)


def to_json(report: ComplianceReport) -> str:
    import json
    return json.dumps(report.to_dict(), indent=2)
