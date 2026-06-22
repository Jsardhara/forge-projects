"""Compliance report generator."""

from __future__ import annotations

from datetime import datetime, timezone
from predictguard.models import (
    Trade,
    ComplianceReport,
    RiskAssessment,
    RiskLevel,
    Jurisdiction,
)


class ReportGenerator:
    """Generates compliance reports from trade data and risk assessments."""

    def __init__(self) -> None:
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"RPT-{self._counter:06d}"

    def generate(
        self,
        trades: list[Trade],
        risk_assessments: list[RiskAssessment],
        period_start: datetime,
        period_end: datetime,
        jurisdiction: Jurisdiction | None = None,
    ) -> ComplianceReport:
        """Generate a compliance report."""
        total_volume = sum(t.quantity * t.price for t in trades)
        flagged = [a for a in risk_assessments if a.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)]

        # Calculate compliance score
        score = 1.0
        findings: list[str] = []
        recommendations: list[str] = []

        if trades:
            flagged_ratio = len(flagged) / len(trades)
            score -= flagged_ratio * 0.5  # Deduct up to 0.5 for flagged trades

            if flagged_ratio > 0.1:
                findings.append(f"High flagged trade ratio: {flagged_ratio:.1%}")
                recommendations.append("Review flagged trades for potential wash trading or manipulation")

            # Check for restricted jurisdiction trades
            restricted_jurisdictions = {"NV", "NJ", "NY", "AZ", "MA"}
            restricted_trades = [
                t for t in trades
                if t.jurisdiction is not None and t.jurisdiction.value in restricted_jurisdictions
            ]
            if restricted_trades:
                score -= 0.2
                findings.append(f"{len(restricted_trades)} trades from restricted jurisdictions")
                recommendations.append("Implement geo-blocking for restricted jurisdictions")

        # Risk assessment findings
        critical_count = sum(1 for a in risk_assessments if a.risk_level == RiskLevel.CRITICAL)
        high_count = sum(1 for a in risk_assessments if a.risk_level == RiskLevel.HIGH)
        if critical_count > 0:
            score -= 0.15 * critical_count
            findings.append(f"{critical_count} CRITICAL risk assessments")
            recommendations.append("Escalate CRITICAL risk assessments to compliance officer immediately")
        if high_count > 0:
            score -= 0.05 * high_count
            findings.append(f"{high_count} HIGH risk assessments")
            recommendations.append("Review HIGH risk assessments within 24 hours")

        score = max(0.0, min(1.0, score))

        return ComplianceReport(
            rid=self._next_id(),
            generated_at=datetime.now(timezone.utc),
            period_start=period_start,
            period_end=period_end,
            jurisdiction=jurisdiction,
            total_trades=len(trades),
            total_volume=round(total_volume, 2),
            flagged_trades=len(flagged),
            risk_assessments=risk_assessments,
            compliance_score=round(score, 4),
            findings=findings,
            recommendations=recommendations,
        )

    @staticmethod
    def format_report(report: ComplianceReport) -> str:
        """Format a compliance report as a human-readable string."""
        lines = [
            "=" * 60,
            f"  COMPLIANCE REPORT — {report.rid}",
            "=" * 60,
            f"  Generated:     {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"  Period:        {report.period_start.strftime('%Y-%m-%d')} to {report.period_end.strftime('%Y-%m-%d')}",
        ]
        if report.jurisdiction is not None:
            lines.append(f"  Jurisdiction:  {report.jurisdiction.value}")
        lines.extend([
            f"  Total Trades:  {report.total_trades}",
            f"  Total Volume:  ${report.total_volume:,.2f}",
            f"  Flagged:       {report.flagged_trades}",
            f"  Compliance:    {report.compliance_score:.0%}",
            "-" * 60,
        ])

        if report.findings:
            lines.append("  FINDINGS:")
            for f in report.findings:
                lines.append(f"    ⚠ {f}")
        else:
            lines.append("  FINDINGS: None")

        lines.append("-" * 60)

        if report.recommendations:
            lines.append("  RECOMMENDATIONS:")
            for r in report.recommendations:
                lines.append(f"    → {r}")
        else:
            lines.append("  RECOMMENDATIONS: None")

        if report.risk_assessments:
            lines.append("-" * 60)
            lines.append("  RISK ASSESSMENTS:")
            for ra in report.risk_assessments:
                lines.append(f"    [{ra.risk_level.value}] {ra.target_type} {ra.target_id}: {ra.risk_score:.2f}")
                for flag in ra.flags:
                    lines.append(f"      • {flag}")

        lines.append("=" * 60)
        return "\n".join(lines)
