"""Gateway — unified facade combining policy, audit, and compliance."""

from __future__ import annotations

from edugate.audit import AuditLogger
from edugate.compliance import ComplianceReport, generate_norway_compliance
from edugate.policy import AccessRequest, PolicyEngine, PolicyResult


class Gateway:
    """Unified AI access gateway for schools."""

    def __init__(
        self,
        school_name: str,
        policy_engine: PolicyEngine | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.school_name = school_name
        self.policy = policy_engine or PolicyEngine()
        self.audit = audit_logger or AuditLogger()

    def check_access(self, request: AccessRequest) -> PolicyResult:
        """Check if a student can access an AI tool."""
        result = self.policy.check(request)
        self.audit.log(
            student_id=request.student.student_id,
            student_name=request.student.name,
            grade=request.student.grade,
            tool_name=request.tool_name,
            decision=result.decision.value,
            reason=result.reason,
            teacher_id=request.teacher_id,
        )
        return result

    def generate_compliance_report(self) -> ComplianceReport:
        """Generate a Norway 2026 compliance report from audit data."""
        events = self.audit.events
        total = len(events)

        elementary = [e for e in events if e.grade <= 7]
        elementary_denied = sum(1 for e in elementary if e.decision == "deny")

        lower_sec = [e for e in events if 8 <= e.grade <= 10]
        lower_sec_supervised = sum(1 for e in lower_sec if "supervis" in e.reason.lower())

        return generate_norway_compliance(
            school_name=self.school_name,
            total_events=total,
            elementary_denied=elementary_denied,
            elementary_total=len(elementary),
            lower_secondary_supervised=lower_sec_supervised,
            lower_secondary_total=len(lower_sec),
            has_audit_trail=total > 0,
            has_policy_configured=True,
        )
