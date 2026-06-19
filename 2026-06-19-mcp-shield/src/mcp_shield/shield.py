"""MCP Shield — unified facade for audit logging, policy enforcement, and compliance."""

from __future__ import annotations

from typing import Optional

from .audit import AuditLogger, AuditSeverity
from .policy import PolicyEngine, PolicyRule, PolicyAction, PolicyDecision
from .compliance import (
    ComplianceReport,
    ComplianceStandard,
    generate_report,
)


class MCPShield:
    """
    Unified security layer for MCP deployments.

    Combines audit logging, policy enforcement, and compliance reporting
    into a single facade. Every tool call passes through the policy engine
    before execution, and the result is logged to the audit trail.
    """

    def __init__(
        self,
        *,
        policy: Optional[PolicyEngine] = None,
        audit: Optional[AuditLogger] = None,
    ):
        self.policy = policy or PolicyEngine()
        self.audit = audit or AuditLogger()

    def check(
        self,
        *,
        agent_id: str,
        tool_name: str,
        server_id: str,
        arguments: Optional[dict] = None,
        session_id: str = "",
    ) -> PolicyDecision:
        """
        Check whether a tool call should be allowed.

        Evaluates policy rules, logs the attempt, and returns the decision.
        """
        decision = self.policy.evaluate(
            agent_id=agent_id,
            tool_name=tool_name,
            server_id=server_id,
            arguments=arguments,
        )

        self.audit.log(
            agent_id=agent_id,
            tool_name=tool_name,
            server_id=server_id,
            arguments=arguments or {},
            action="tool_call",
            decision=decision.action.value,
            risk_score=decision.risk_score,
            reason=decision.reason,
            session_id=session_id,
            metadata={"rule_name": decision.rule_name},
        )

        return decision

    def add_policy_rule(self, rule: PolicyRule) -> None:
        self.policy.add_rule(rule)

    def remove_policy_rule(self, name: str) -> bool:
        return self.policy.remove_rule(name)

    def generate_compliance_report(
        self,
        agent_id: str,
        standard: ComplianceStandard = ComplianceStandard.SOC2,
        period_start: str = "",
        period_end: str = "",
    ) -> ComplianceReport:
        return generate_report(
            self.audit,
            agent_id,
            standard=standard,
            period_start=period_start,
            period_end=period_end,
        )

    def get_audit_summary(self) -> dict:
        return self.audit.summary()

    def get_critical_events(self) -> list:
        return self.audit.get_critical_events()
