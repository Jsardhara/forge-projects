"""Tests for AgentIAM — Main Facade (integration tests)."""

import pytest
from agentiam import AgentIAM, AgentStatus


@pytest.fixture
def iam():
    return AgentIAM()


@pytest.fixture
def agent(iam):
    return iam.register_agent(
        name="test-agent",
        owner="alice",
        scopes=["read", "write"],
    )


@pytest.fixture
def policy(iam):
    return iam.policies.create_policy(
        name="test-policy",
        allowed_scopes=["read", "write"],
        denied_scopes=["admin:*"],
    )


class TestRegisterAgent:
    def test_registers_and_audits(self, iam):
        agent = iam.register_agent(name="bot", owner="alice")
        assert agent.is_active
        assert iam.audit.count() == 1
        assert iam.audit.all()[0].action == "register"


class TestIssueCredential:
    def test_issue_and_audit(self, iam, agent):
        cred = iam.issue_credential(agent.agent_id)
        assert cred.is_valid
        assert iam.audit.count() == 2  # register + issue


class TestValidateCredential:
    def test_validate(self, iam, agent):
        cred = iam.issue_credential(agent.agent_id)
        validated = iam.validate_credential(cred.token)
        assert validated.agent_id == agent.agent_id

    def test_validate_invalid(self, iam, agent):
        with pytest.raises(PermissionError):
            iam.validate_credential("fake-token")


class TestCheckAccess:
    def test_allowed(self, iam, agent, policy):
        cred = iam.issue_credential(agent.agent_id)
        allowed, reason = iam.check_access(cred.token, ["read"], policy.policy_id)
        assert allowed is True

    def test_denied_by_scope(self, iam, agent, policy):
        cred = iam.issue_credential(agent.agent_id)
        allowed, reason = iam.check_access(cred.token, ["admin:*"], policy.policy_id)
        assert allowed is False

    def test_denied_by_invalid_token(self, iam, agent, policy):
        allowed, reason = iam.check_access("fake-token", ["read"], policy.policy_id)
        assert allowed is False

    def test_denied_by_chain_depth(self, iam, agent, policy):
        cred = iam.issue_credential(agent.agent_id)
        allowed, reason = iam.check_access(cred.token, ["read"], policy.policy_id, chain_depth=99)
        assert allowed is False


class TestRevokeAgent:
    def test_revokes_agent_and_credentials(self, iam, agent):
        cred = iam.issue_credential(agent.agent_id)
        iam.revoke_agent(agent.agent_id)
        assert agent.status == AgentStatus.REVOKED
        # Credential should also be revoked
        with pytest.raises(PermissionError):
            iam.validate_credential(cred.token)

    def test_audit_trail(self, iam, agent):
        iam.revoke_agent(agent.agent_id)
        revoke_events = [e for e in iam.audit.all() if e.action == "revoke"]
        assert len(revoke_events) == 1


class TestSuspendAgent:
    def test_suspend(self, iam, agent):
        iam.suspend_agent(agent.agent_id)
        assert agent.status == AgentStatus.SUSPENDED
        # Cannot issue new credentials
        with pytest.raises(PermissionError):
            iam.issue_credential(agent.agent_id)


class TestFullLifecycle:
    def test_complete_flow(self, iam):
        # 1. Register
        agent = iam.register_agent(
            name="lifecycle-bot",
            owner="team",
            scopes=["data:read", "data:write"],
        )
        assert agent.is_active

        # 2. Create policy
        pol = iam.policies.create_policy(
            name="data-policy",
            allowed_scopes=["data:read", "data:write"],
            denied_scopes=["admin:*"],
        )

        # 3. Issue credential
        cred = iam.issue_credential(agent.agent_id, ttl=300)
        assert cred.is_valid

        # 4. Check access — allowed
        allowed, _ = iam.check_access(cred.token, ["data:read"], pol.policy_id)
        assert allowed is True

        # 5. Check access — denied
        allowed, _ = iam.check_access(cred.token, ["admin:*"], pol.policy_id)
        assert allowed is False

        # 6. Rotate credential
        new_cred = iam.credentials.rotate(cred.credential_id)
        assert new_cred.is_valid
        with pytest.raises(PermissionError):
            iam.validate_credential(cred.token)

        # 7. Revoke agent
        iam.revoke_agent(agent.agent_id)
        assert agent.status == AgentStatus.REVOKED

        # 8. Audit trail
        assert iam.audit.count() >= 5
