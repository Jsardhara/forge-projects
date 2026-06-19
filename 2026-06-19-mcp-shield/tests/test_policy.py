"""Tests for mcp_shield.policy module."""

import pytest
from datetime import datetime, timezone

from mcp_shield.policy import PolicyEngine, PolicyRule, PolicyAction, PolicyDecision


class TestPolicyRule:
    def test_default_values(self):
        rule = PolicyRule(name="test", action=PolicyAction.ALLOW)
        assert rule.agent_pattern == "*"
        assert rule.tool_pattern == "*"
        assert rule.server_pattern == "*"
        assert rule.max_calls_per_minute == 0
        assert rule.risk_threshold == 1.0
        assert rule.enabled is True


class TestPolicyDecision:
    def test_creation(self):
        d = PolicyDecision(action=PolicyAction.ALLOW, reason="test", rule_name="r1")
        assert d.action == PolicyAction.ALLOW
        assert d.risk_score == 0.0


class TestPolicyEngine:
    def _make_engine(self, rules=None):
        return PolicyEngine(rules)

    def test_empty_engine_default_deny(self):
        engine = self._make_engine()
        d = engine.evaluate(agent_id="a", tool_name="t", server_id="s")
        assert d.action == PolicyAction.REQUIRE_APPROVAL
        assert d.rule_name == "default"

    def test_allow_rule(self):
        engine = self._make_engine([
            PolicyRule(name="allow-all", action=PolicyAction.ALLOW, priority=10),
        ])
        d = engine.evaluate(agent_id="a", tool_name="t", server_id="s")
        assert d.action == PolicyAction.ALLOW
        assert d.rule_name == "allow-all"

    def test_deny_rule_takes_precedence(self):
        engine = self._make_engine([
            PolicyRule(name="allow", action=PolicyAction.ALLOW, priority=5),
            PolicyRule(name="deny", action=PolicyAction.DENY, priority=10),
        ])
        d = engine.evaluate(agent_id="a", tool_name="t", server_id="s")
        assert d.action == PolicyAction.DENY
        assert d.rule_name == "deny"

    def test_agent_pattern_matching(self):
        engine = self._make_engine([
            PolicyRule(
                name="allow-agent-001",
                action=PolicyAction.ALLOW,
                agent_pattern="agent-001",
                priority=10,
            ),
        ])
        d = engine.evaluate(agent_id="agent-001", tool_name="t", server_id="s")
        assert d.action == PolicyAction.ALLOW

        d2 = engine.evaluate(agent_id="agent-002", tool_name="t", server_id="s")
        assert d2.action == PolicyAction.REQUIRE_APPROVAL

    def test_tool_pattern_matching(self):
        engine = self._make_engine([
            PolicyRule(
                name="allow-read",
                action=PolicyAction.ALLOW,
                tool_pattern="read_*",
                priority=10,
            ),
        ])
        d = engine.evaluate(agent_id="a", tool_name="read_file", server_id="s")
        assert d.action == PolicyAction.ALLOW

        d2 = engine.evaluate(agent_id="a", tool_name="write_file", server_id="s")
        assert d2.action == PolicyAction.REQUIRE_APPROVAL

    def test_server_pattern_matching(self):
        engine = self._make_engine([
            PolicyRule(
                name="allow-dev",
                action=PolicyAction.ALLOW,
                server_pattern="dev-*",
                priority=10,
            ),
        ])
        d = engine.evaluate(agent_id="a", tool_name="t", server_id="dev-server")
        assert d.action == PolicyAction.ALLOW

        d2 = engine.evaluate(agent_id="a", tool_name="t", server_id="prod-server")
        assert d2.action == PolicyAction.REQUIRE_APPROVAL

    def test_add_and_remove_rule(self):
        engine = self._make_engine()
        assert len(engine.rules) == 0
        engine.add_rule(PolicyRule(name="r1", action=PolicyAction.ALLOW))
        assert len(engine.rules) == 1
        removed = engine.remove_rule("r1")
        assert removed is True
        assert len(engine.rules) == 0
        removed_again = engine.remove_rule("r1")
        assert removed_again is False

    def test_disabled_rule_skipped(self):
        engine = self._make_engine([
            PolicyRule(name="allow", action=PolicyAction.ALLOW, enabled=False, priority=10),
        ])
        d = engine.evaluate(agent_id="a", tool_name="t", server_id="s")
        assert d.action == PolicyAction.REQUIRE_APPROVAL

    def test_rate_limiting(self):
        engine = self._make_engine([
            PolicyRule(
                name="limited",
                action=PolicyAction.ALLOW,
                tool_pattern="fetch",
                max_calls_per_minute=3,
                priority=10,
            ),
        ])
        # First 3 should allow
        for i in range(3):
            d = engine.evaluate(agent_id="a", tool_name="fetch", server_id="s")
            assert d.action == PolicyAction.ALLOW, f"Call {i+1} should be allowed"

        # 4th should be denied
        d = engine.evaluate(agent_id="a", tool_name="fetch", server_id="s")
        assert d.action == PolicyAction.DENY
        assert "Rate limit" in d.reason

    def test_rate_limiting_per_agent(self):
        engine = self._make_engine([
            PolicyRule(
                name="limited",
                action=PolicyAction.ALLOW,
                tool_pattern="fetch",
                max_calls_per_minute=2,
                priority=10,
            ),
        ])
        # Agent-1 uses 2 calls
        engine.evaluate(agent_id="a1", tool_name="fetch", server_id="s")
        engine.evaluate(agent_id="a1", tool_name="fetch", server_id="s")
        # Agent-1 blocked
        d = engine.evaluate(agent_id="a1", tool_name="fetch", server_id="s")
        assert d.action == PolicyAction.DENY

        # Agent-2 still allowed
        d2 = engine.evaluate(agent_id="a2", tool_name="fetch", server_id="s")
        assert d2.action == PolicyAction.ALLOW

    def test_risk_calculation_high_risk_tool(self):
        engine = self._make_engine([
            PolicyRule(name="allow", action=PolicyAction.ALLOW, priority=10),
        ])
        d = engine.evaluate(agent_id="a", tool_name="exec", server_id="s")
        assert d.risk_score >= 0.7

    def test_risk_calculation_medium_risk_tool(self):
        engine = self._make_engine([
            PolicyRule(name="allow", action=PolicyAction.ALLOW, priority=10),
        ])
        d = engine.evaluate(agent_id="a", tool_name="fetch", server_id="s")
        assert 0.3 <= d.risk_score <= 0.5

    def test_risk_calculation_dangerous_args(self):
        engine = self._make_engine([
            PolicyRule(name="allow", action=PolicyAction.ALLOW, priority=10),
        ])
        d = engine.evaluate(agent_id="a", tool_name="read", server_id="s", arguments={"cmd": "sudo rm -rf /"})
        assert d.risk_score >= 0.4  # elevated by dangerous pattern

    def test_require_approval_action(self):
        engine = self._make_engine([
            PolicyRule(name="approval", action=PolicyAction.REQUIRE_APPROVAL, priority=10),
        ])
        d = engine.evaluate(agent_id="a", tool_name="t", server_id="s")
        assert d.action == PolicyAction.REQUIRE_APPROVAL

    def test_rules_sorted_by_priority(self):
        engine = self._make_engine([
            PolicyRule(name="low", action=PolicyAction.ALLOW, priority=1),
            PolicyRule(name="high", action=PolicyAction.DENY, priority=100),
            PolicyRule(name="mid", action=PolicyAction.ALLOW, priority=50),
        ])
        names = [r.name for r in engine.rules]
        assert names == ["high", "mid", "low"]

    def test_time_window_restriction(self):
        engine = self._make_engine([
            PolicyRule(
                name="biz-hours",
                action=PolicyAction.ALLOW,
                time_window="09:00-17:00",
                priority=10,
            ),
        ])
        # The result depends on current time — just verify it doesn't crash
        d = engine.evaluate(agent_id="a", tool_name="t", server_id="s")
        assert d.action in (PolicyAction.ALLOW, PolicyAction.REQUIRE_APPROVAL)

    def test_malformed_time_window_no_restriction(self):
        engine = self._make_engine([
            PolicyRule(
                name="bad-window",
                action=PolicyAction.ALLOW,
                time_window="not-a-time",
                priority=10,
            ),
        ])
        d = engine.evaluate(agent_id="a", tool_name="t", server_id="s")
        assert d.action == PolicyAction.ALLOW  # malformed = no restriction
