"""Compliance report generator for MCP audit data."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .audit import AuditLogger


class ComplianceStandard(str, Enum):
    SOC2 = "soc2"
    GDPR = "gdpr"
    ISO27001 = "iso27001"
    HIPAA = "hipaa"


@dataclass
class ComplianceFinding:
    """A single compliance finding."""
    standard: str
    control: str
    status: str  # "pass", "fail", "warning"
    description: str
    evidence: str = ""


@dataclass
class ComplianceReport:
    """Compliance assessment report based on audit events."""
    generated_at: str
    standard: ComplianceStandard
    agent_id: str
    period_start: str
    period_end: str
    total_events: int = 0
    critical_events: int = 0
    denied_events: int = 0
    avg_risk: float = 0.0
    findings: list[ComplianceFinding] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def is_compliant(self) -> bool:
        return all(f.status != "fail" for f in self.findings)

    def summary(self) -> dict:
        status_counts: dict[str, int] = {}
        for f in self.findings:
            status_counts[f.status] = status_counts.get(f.status, 0) + 1
        return {
            "standard": self.standard.value,
            "agent_id": self.agent_id,
            "generated_at": self.generated_at,
            "total_events": self.total_events,
            "critical_events": self.critical_events,
            "denied_events": self.denied_events,
            "avg_risk": self.avg_risk,
            "compliant": self.is_compliant(),
            "findings": status_counts,
            "recommendations": len(self.recommendations),
        }

    def to_json(self) -> str:
        return json.dumps(self.summary(), indent=2)


def generate_report(
    audit: "AuditLogger",
    agent_id: str,
    standard: ComplianceStandard = ComplianceStandard.SOC2,
    period_start: str = "",
    period_end: str = "",
) -> ComplianceReport:
    """Generate a compliance report from audit events."""
    events = audit.filter_by_agent(agent_id)
    now = datetime.now(timezone.utc).isoformat()

    if period_start:
        from datetime import datetime as dt
        start = dt.fromisoformat(period_start)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        end = dt.fromisoformat(period_end) if period_end else dt.now(timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        events = [e for e in events
                  if _parse_ts(e.timestamp) >= start and _parse_ts(e.timestamp) <= end]

    critical = [e for e in events if e.severity == "critical"]
    denied = audit.filter_by_decision("deny")
    denied_for_agent = [e for e in denied if e.agent_id == agent_id]
    avg_risk = (
        round(sum(e.risk_score for e in events) / len(events), 3)
        if events else 0.0
    )

    findings = _assess_findings(audit, agent_id, standard, events, critical, denied_for_agent)
    recommendations = _generate_recommendations(findings, events, agent_id)

    return ComplianceReport(
        generated_at=now,
        standard=standard,
        agent_id=agent_id,
        period_start=period_start or (events[0].timestamp if events else now),
        period_end=period_end or now,
        total_events=len(events),
        critical_events=len(critical),
        denied_events=len(denied_for_agent),
        avg_risk=avg_risk,
        findings=findings,
        recommendations=recommendations,
    )


def _parse_ts(ts_str: str) -> datetime:
    from datetime import datetime as dt
    ts = dt.fromisoformat(ts_str)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _assess_findings(
    audit: "AuditLogger",
    agent_id: str,
    standard: ComplianceStandard,
    events: list,
    critical: list,
    denied: list,
) -> list[ComplianceFinding]:
    findings = []

    if standard == ComplianceStandard.SOC2 or standard == ComplianceStandard.ISO27001:
        # Access control
        if denied:
            findings.append(ComplianceFinding(
                standard=standard.value,
                control="AC-1",
                status="pass",
                description=f"{len(denied)} unauthorized access attempts blocked",
                evidence=f"Events: {[e.event_id for e in denied[:5]]}",
            ))
        else:
            findings.append(ComplianceFinding(
                standard=standard.value,
                control="AC-1",
                status="warning",
                description="No denied events found — verify policy rules are active",
            ))

        # Audit trail completeness
        if events:
            findings.append(ComplianceFinding(
                standard=standard.value,
                control="AU-2",
                status="pass",
                description=f"{len(events)} events logged with agent identity and timestamp",
            ))
        else:
            findings.append(ComplianceFinding(
                standard=standard.value,
                control="AU-2",
                status="fail",
                description="No audit events found — audit logging may not be active",
            ))

        # Risk monitoring
        if critical:
            findings.append(ComplianceFinding(
                standard=standard.value,
                control="SI-4",
                status="warning",
                description=f"{len(critical)} critical-severity events detected",
                evidence=f"Tools: {list(set(e.tool_name for e in critical))}",
            ))
        else:
            findings.append(ComplianceFinding(
                standard=standard.value,
                control="SI-4",
                status="pass",
                description="No critical-severity events in period",
            ))

    if standard == ComplianceStandard.GDPR:
        # Data access logging
        if events:
            findings.append(ComplianceFinding(
                standard="gdpr",
                control="Art-30",
                status="pass",
                description=f"{len(events)} processing activities recorded",
            ))
        else:
            findings.append(ComplianceFinding(
                standard="gdpr",
                control="Art-30",
                status="fail",
                description="No processing activity records found",
            ))

        # Purpose limitation
        tools_used = set(e.tool_name for e in events)
        if len(tools_used) > 10:
            findings.append(ComplianceFinding(
                standard="gdpr",
                control="Art-5(1)(b)",
                status="warning",
                description=f"Agent accessed {len(tools_used)} distinct tools — verify purpose limitation",
            ))
        else:
            findings.append(ComplianceFinding(
                standard="gdpr",
                control="Art-5(1)(b)",
                status="pass",
                description=f"Agent accessed {len(tools_used)} tools — within reasonable scope",
            ))

    return findings


def _generate_recommendations(
    findings: list[ComplianceFinding],
    events: list,
    agent_id: str,
) -> list[str]:
    recs = []
    fail_count = sum(1 for f in findings if f.status == "fail")
    warn_count = sum(1 for f in findings if f.status == "warning")

    if fail_count > 0:
        recs.append(f"URGENT: {fail_count} failing compliance finding(s) need immediate attention")
    if warn_count > 0:
        recs.append(f"Review {warn_count} warning(s) to strengthen compliance posture")

    if events:
        tools = set(e.tool_name for e in events)
        if len(tools) > 5:
            recs.append(f"Agent '{agent_id}' uses {len(tools)} tools — consider narrowing scope to minimum required")

        high_risk = [e for e in events if e.risk_score >= 0.7]
        if high_risk:
            recs.append(f"{len(high_risk)} high-risk tool calls detected — review and add explicit deny rules if needed")

    if not recs:
        recs.append("Compliance posture is strong — continue regular monitoring")

    return recs
