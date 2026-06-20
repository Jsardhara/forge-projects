"""Compliance reporting for education AI regulations."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone


@dataclasses.dataclass
class ComplianceFinding:
    """A single compliance finding."""
    framework: str
    control_id: str
    description: str
    status: str  # "pass", "fail", "warning"
    evidence: str


@dataclasses.dataclass
class ComplianceReport:
    """A compliance report for education AI regulations."""
    report_id: str
    generated_at: str
    framework: str
    school_name: str
    findings: list[ComplianceFinding]
    summary: str


def generate_norway_compliance(
    school_name: str,
    total_events: int,
    elementary_denied: int,
    elementary_total: int,
    lower_secondary_supervised: int,
    lower_secondary_total: int,
    has_audit_trail: bool,
    has_policy_configured: bool,
) -> ComplianceReport:
    """Generate a compliance report for Norway's August 2026 AI regulations.

    Norway's rules:
    - Grades 1-7 (ages 6-13): Generally no AI use
    - Grades 8-10 (ages 14-16): AI allowed only under teacher supervision
    - Grades 11-13 (ages 17-19): AI allowed with appropriate use training
    """
    findings: list[ComplianceFinding] = []

    # Policy configuration check
    if has_policy_configured:
        findings.append(ComplianceFinding(
            framework="Norway-2026",
            control_id="POL-001",
            description="AI access policies are configured for all grade bands",
            status="pass",
            evidence="Policy engine has rules for elementary, lower secondary, and upper secondary",
        ))
    else:
        findings.append(ComplianceFinding(
            framework="Norway-2026",
            control_id="POL-001",
            description="AI access policies must be configured for all grade bands",
            status="fail",
            evidence="No policies configured in the system",
        ))

    # Elementary school ban compliance
    if elementary_total > 0:
        compliance_rate = elementary_denied / elementary_total
        if compliance_rate >= 0.95:
            findings.append(ComplianceFinding(
                framework="Norway-2026",
                control_id="ELEM-001",
                description=f"Elementary AI ban enforced ({elementary_denied}/{elementary_total} requests denied)",
                status="pass",
                evidence=f"{compliance_rate:.1%} denial rate for grades 1-7",
            ))
        else:
            findings.append(ComplianceFinding(
                framework="Norway-2026",
                control_id="ELEM-001",
                description=f"Elementary AI ban not fully enforced ({elementary_denied}/{elementary_total} denied)",
                status="fail",
                evidence=f"Only {compliance_rate:.1%} denial rate — below 95% threshold",
            ))
    else:
        findings.append(ComplianceFinding(
            framework="Norway-2026",
            control_id="ELEM-001",
            description="No elementary AI access requests recorded",
            status="pass",
            evidence="Zero requests from grades 1-7 (clean log)",
        ))

    # Lower secondary supervision compliance
    if lower_secondary_total > 0:
        supervision_rate = lower_secondary_supervised / lower_secondary_total
        if supervision_rate >= 0.90:
            findings.append(ComplianceFinding(
                framework="Norway-2026",
                control_id="LOWSEC-001",
                description=f"Lower secondary AI use properly supervised ({lower_secondary_supervised}/{lower_secondary_total})",
                status="pass",
                evidence=f"{supervision_rate:.1%} supervision rate for grades 8-10",
            ))
        else:
            findings.append(ComplianceFinding(
                framework="Norway-2026",
                control_id="LOWSEC-001",
                description=f"Lower secondary AI use not adequately supervised ({lower_secondary_supervised}/{lower_secondary_total})",
                status="warning",
                evidence=f"Only {supervision_rate:.1%} supervision rate — below 90% threshold",
            ))
    else:
        findings.append(ComplianceFinding(
            framework="Norway-2026",
            control_id="LOWSEC-001",
            description="No lower secondary AI access requests recorded",
            status="pass",
            evidence="Zero requests from grades 8-10 (clean log)",
        ))

    # Audit trail check
    if has_audit_trail:
        findings.append(ComplianceFinding(
            framework="Norway-2026",
            control_id="AUDIT-001",
            description=f"Audit trail maintained ({total_events} events logged)",
            status="pass",
            evidence="All AI access events are logged with timestamps and decisions",
        ))
    else:
        findings.append(ComplianceFinding(
            framework="Norway-2026",
            control_id="AUDIT-001",
            description="No audit trail available",
            status="fail",
            evidence="Audit logging is not enabled",
        ))

    # Overall summary
    fail_count = sum(1 for f in findings if f.status == "fail")
    warn_count = sum(1 for f in findings if f.status == "warning")
    pass_count = sum(1 for f in findings if f.status == "pass")

    if fail_count == 0 and warn_count == 0:
        summary = f"FULLY COMPLIANT — All {pass_count} controls passed for Norway 2026 regulations."
    elif fail_count == 0:
        summary = f"MOSTLY COMPLIANT — {pass_count} passed, {warn_count} warnings. Review warnings."
    else:
        summary = f"NON-COMPLIANT — {fail_count} failures, {warn_count} warnings, {pass_count} passed. Immediate action required."

    return ComplianceReport(
        report_id=f"NO-WAY-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        generated_at=datetime.now(timezone.utc).isoformat(),
        framework="Norway-2026",
        school_name=school_name,
        findings=findings,
        summary=summary,
    )
