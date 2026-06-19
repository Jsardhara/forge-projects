"""Tests for mcp_shield.shield module (integration tests)."""

import pytest

from mcp_shield.shield import MCPShield
from mcp_shield.policy import PolicyRule, PolicyAction
from mcp_shield.compliance import ComplianceStandard


class TestMCPShield:
    def _make_shield(self):
        shield = MCPShield()
        shield.add_policy_rule(PolicyRule(
            name="allow-read",
            action=PolicyAction.ALLOW,
            tool_pattern="read_*",
            priority=10,
        ))
        shield.add_policy_rule(PolicyRule(
            name="deny-exec",
            action=PolicyAction.DENY,
            tool_pattern="exec",
            priority=20,
        ))
        return shield

    def test_check_allowed(self):
        shield = self._make_shield()
        decision = shield.check(
            agent_id="agent-001",
            tool_name="read_file",
            server_id="dev",
            arguments={"path": "/tmp/test.txt"},
        )
        assert decision.action == PolicyAction.ALLOW

    def test_check_denied(self):
        shield = self._make_shield()
        decision = shield.check(
            agent_id="agent-001",
            tool_name="exec",
            server_id="dev",
            arguments={"command": "ls"},
        )
        assert decision.action == PolicyAction.DENY

    def test_check_requires_approval(self):
        shield = self._make_shield()
        decision = shield.check(
            agent_id="agent-001",
            tool_name="write_file",
            server_id="dev",
            arguments={"path": "/tmp/out.txt"},
        )
        assert decision.action == PolicyAction.REQUIRE_APPROVAL

    def test_audit_populated_after_checks(self):
        shield = self._make_shield()
        shield.check(agent_id="a1", tool_name="read_file", server_id="s", arguments={})
        shield.check(agent_id="a1", tool_name="exec", server_id="s", arguments={})
        summary = shield.get_audit_summary()
        assert summary["total"] == 2
        assert summary["by_decision"]["allow"] == 1
        assert summary["by_decision"]["deny"] == 1

    def test_compliance_report_generation(self):
        shield = self._make_shield()
        for _ in range(3):
            shield.check(agent_id="a1", tool_name="read_file", server_id="s", arguments={})
        shield.check(agent_id="a1", tool_name="exec", server_id="s", arguments={})

        report = shield.generate_compliance_report("a1", ComplianceStandard.SOC2)
        assert report.agent_id == "a1"
        assert report.total_events == 4
        assert report.denied_events == 1

    def test_critical_events(self):
        shield = self._make_shield()
        shield.check(
            agent_id="a1", tool_name="exec", server_id="s",
            arguments={"command": "sudo rm -rf /"},
        )
        critical = shield.get_critical_events()
        assert len(critical) == 1
        assert critical[0].risk_score >= 0.7

    def test_add_and_remove_policy_rule(self):
        shield = MCPShield()
        assert len(shield.policy.rules) == 0
        shield.add_policy_rule(PolicyRule(name="r1", action=PolicyAction.ALLOW))
        assert len(shield.policy.rules) == 1
        removed = shield.remove_policy_rule("r1")
        assert removed is True
        assert len(shield.policy.rules) == 0

    def test_full_workflow(self):
        """End-to-end: policy check → audit → compliance report."""
        shield = MCPShield()
        shield.add_policy_rule(PolicyRule(
            name="allow-read", action=PolicyAction.ALLOW,
            tool_pattern="read_*", priority=10,
        ))
        shield.add_policy_rule(PolicyRule(
            name="deny-exec", action=PolicyAction.DENY,
            tool_pattern="exec", priority=20,
        ))

        # Simulate 10 tool calls
        for i in range(8):
            shield.check(
                agent_id="agent-001",
                tool_name="read_file",
                server_id="dev",
                arguments={"path": f"/file{i}.txt"},
                session_id="session-abc",
            )
        shield.check(
            agent_id="agent-001",
            tool_name="exec",
            server_id="dev",
            arguments={"command": "ls"},
            session_id="session-abc",
        )
        shield.check(
            agent_id="agent-001",
            tool_name="exec",
            server_id="dev",
            arguments={"command": "sudo rm -rf /"},
            session_id="session-abc",
        )

        # Verify audit
        summary = shield.get_audit_summary()
        assert summary["total"] == 10
        assert summary["by_decision"]["allow"] == 8
        assert summary["by_decision"]["deny"] == 2

        # Verify compliance
        report = shield.generate_compliance_report("agent-001")
        assert report.total_events == 10
        assert report.denied_events == 2
        assert len(report.findings) > 0
        assert len(report.recommendations) > 0

    def test_multiple_agents_isolated(self):
        shield = self._make_shield()
        shield.check(agent_id="a1", tool_name="read_file", server_id="s", arguments={})
        shield.check(agent_id="a2", tool_name="read_file", server_id="s", arguments={})
        shield.check(agent_id="a1", tool_name="exec", server_id="s", arguments={})

        summary = shield.get_audit_summary()
        assert summary["by_agent"]["a1"] == 2
        assert summary["by_agent"]["a2"] == 1

        report_a1 = shield.generate_compliance_report("a1")
        assert report_a1.total_events == 2

        report_a2 = shield.generate_compliance_report("a2")
        assert report_a2.total_events == 1
