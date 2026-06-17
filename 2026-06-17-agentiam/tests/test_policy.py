"""Tests for AgentIAM — Policy Engine."""

import pytest
from agentiam import AgentIAM, PolicyEngine, AccessPolicy


@pytest.fixture
def engine():
    return PolicyEngine()


@pytest.fixture
def iam():
    return AgentIAM()


class TestCreatePolicy:
    def test_create_basic(self, engine):
        pol = engine.create_policy(name="test-policy")
        assert pol.policy_id.startswith("pol-")
        assert pol.name == "test-policy"
        assert pol.allowed_scopes == []

    def test_create_with_all_fields(self, engine):
        pol = engine.create_policy(
            name="restricted",
            description="Restricted access",
            allowed_scopes=["read"],
            denied_scopes=["admin:*"],
            max_chain_depth=2,
            require_human_approval=True,
            rate_limit_per_minute=10,
        )
        assert pol.allowed_scopes == ["read"]
        assert pol.denied_scopes == ["admin:*"]
        assert pol.max_chain_depth == 2
        assert pol.require_human_approval is True
        assert pol.rate_limit_per_minute == 10


class TestEvaluate:
    def test_allow_all_when_no_allowed_scopes(self, engine):
        pol = engine.create_policy(name="permissive")
        allowed, reason = engine.evaluate(pol.policy_id, ["anything"])
        assert allowed is True

    def test_allow_when_scope_in_allowed_list(self, engine):
        pol = engine.create_policy(name="restricted", allowed_scopes=["read", "write"])
        allowed, _ = engine.evaluate(pol.policy_id, ["read"])
        assert allowed is True

    def test_deny_when_scope_not_in_allowed_list(self, engine):
        pol = engine.create_policy(name="restricted", allowed_scopes=["read"])
        allowed, reason = engine.evaluate(pol.policy_id, ["admin"])
        assert allowed is False
        assert "not in allowed" in reason

    def test_deny_when_scope_explicitly_denied(self, engine):
        pol = engine.create_policy(name="no-admin", allowed_scopes=["read", "admin"], denied_scopes=["admin"])
        allowed, reason = engine.evaluate(pol.policy_id, ["admin"])
        assert allowed is False
        assert "explicitly denied" in reason

    def test_deny_when_chain_depth_exceeded(self, engine):
        pol = create_policy = engine.create_policy(name="depth", max_chain_depth=2)
        allowed, reason = engine.evaluate(pol.policy_id, ["read"], chain_depth=3)
        assert allowed is False
        assert "Chain depth" in reason

    def test_deny_when_human_approval_required(self, engine):
        pol = engine.create_policy(name="human-gate", require_human_approval=True)
        allowed, reason = engine.evaluate(pol.policy_id, ["read"])
        assert allowed is False
        assert "Human approval" in reason

    def test_deny_when_policy_not_found(self, engine):
        allowed, reason = engine.evaluate("pol-nonexistent", ["read"])
        assert allowed is False
        assert "not found" in reason

    def test_allow_multiple_scopes(self, engine):
        pol = engine.create_policy(name="multi", allowed_scopes=["read", "write", "list"])
        allowed, _ = engine.evaluate(pol.policy_id, ["read", "write"])
        assert allowed is True

    def test_deny_if_any_scope_not_allowed(self, engine):
        pol = engine.create_policy(name="strict", allowed_scopes=["read"])
        allowed, _ = engine.evaluate(pol.policy_id, ["read", "admin"])
        assert allowed is False


class TestGetPolicy:
    def test_get_existing(self, engine):
        pol = engine.create_policy(name="test")
        found = engine.get_policy(pol.policy_id)
        assert found is not None
        assert found.name == "test"

    def test_get_missing(self, engine):
        assert engine.get_policy("pol-nonexistent") is None


class TestListPolicies:
    def test_list_empty(self, engine):
        assert engine.list_policies() == []

    def test_list_multiple(self, engine):
        engine.create_policy(name="p1")
        engine.create_policy(name="p2")
        assert len(engine.list_policies()) == 2
