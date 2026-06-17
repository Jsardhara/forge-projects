"""Tests for AgentIAM — Credential Manager."""

import pytest
from datetime import datetime, timezone, timedelta
from agentiam import AgentIAM, AgentStatus, CredentialStatus


@pytest.fixture
def iam():
    return AgentIAM()


@pytest.fixture
def agent(iam):
    return iam.register_agent(name="test-agent", owner="alice", scopes=["read", "write"])


class TestIssue:
    def test_issue_basic(self, iam, agent):
        cred = iam.credentials.issue(agent.agent_id)
        assert cred.agent_id == agent.agent_id
        assert cred.credential_id.startswith("cred-")
        assert len(cred.token) > 30
        assert cred.status == CredentialStatus.ACTIVE

    def test_issue_with_scopes(self, iam, agent):
        cred = iam.credentials.issue(agent.agent_id, scopes=["admin:*"])
        assert cred.scopes == ["admin:*"]

    def test_issue_inherits_agent_scopes(self, iam, agent):
        cred = iam.credentials.issue(agent.agent_id)
        assert cred.scopes == ["read", "write"]

    def test_issue_with_ttl(self, iam, agent):
        cred = iam.credentials.issue(agent.agent_id, ttl=60)
        remaining = cred.time_remaining()
        assert 55 <= remaining <= 60

    def test_issue_for_missing_agent(self, iam):
        with pytest.raises(KeyError):
            iam.credentials.issue("agent-nonexistent")

    def test_issue_for_suspended_agent(self, iam, agent):
        iam.suspend_agent(agent.agent_id)
        with pytest.raises(PermissionError, match="suspended"):
            iam.credentials.issue(agent.agent_id)

    def test_issue_for_revoked_agent(self, iam, agent):
        iam.revoke_agent(agent.agent_id)
        with pytest.raises(PermissionError, match="revoked"):
            iam.credentials.issue(agent.agent_id)


class TestValidate:
    def test_validate_valid(self, iam, agent):
        cred = iam.credentials.issue(agent.agent_id)
        validated = iam.credentials.validate(cred.token)
        assert validated.credential_id == cred.credential_id

    def test_validate_invalid_token(self, iam, agent):
        with pytest.raises(PermissionError, match="Invalid"):
            iam.credentials.validate("totally-fake-token")

    def test_validate_expired(self, iam, agent):
        cred = iam.credentials.issue(agent.agent_id, ttl=0)
        import time
        time.sleep(0.1)
        with pytest.raises(PermissionError, match="expired"):
            iam.credentials.validate(cred.token)

    def test_validate_revoked_cred(self, iam, agent):
        cred = iam.credentials.issue(agent.agent_id)
        iam.credentials.revoke(cred.credential_id)
        with pytest.raises(PermissionError, match="revoked"):
            iam.credentials.validate(cred.token)


class TestRevoke:
    def test_revoke(self, iam, agent):
        cred = iam.credentials.issue(agent.agent_id)
        revoked = iam.credentials.revoke(cred.credential_id)
        assert revoked.status == CredentialStatus.REVOKED

    def test_revoke_missing(self, iam, agent):
        with pytest.raises(KeyError):
            iam.credentials.revoke("cred-nonexistent")


class TestRotate:
    def test_rotate(self, iam, agent):
        old = iam.credentials.issue(agent.agent_id, scopes=["read"])
        new = iam.credentials.rotate(old.credential_id)
        assert new.credential_id != old.credential_id
        assert new.agent_id == agent.agent_id
        assert new.scopes == ["read"]
        # Old should be revoked
        with pytest.raises(PermissionError):
            iam.credentials.validate(old.token)
        # New should be valid
        validated = iam.credentials.validate(new.token)
        assert validated.credential_id == new.credential_id

    def test_rotate_missing(self, iam, agent):
        with pytest.raises(KeyError):
            iam.credentials.rotate("cred-nonexistent")


class TestListForAgent:
    def test_list(self, iam, agent):
        iam.credentials.issue(agent.agent_id)
        iam.credentials.issue(agent.agent_id)
        creds = iam.credentials.list_for_agent(agent.agent_id)
        assert len(creds) == 2

    def test_list_empty(self, iam, agent):
        assert iam.credentials.list_for_agent(agent.agent_id) == []


class TestCredentialProperties:
    def test_is_valid(self, iam, agent):
        cred = iam.credentials.issue(agent.agent_id)
        assert cred.is_valid is True

    def test_is_not_valid_when_revoked(self, iam, agent):
        cred = iam.credentials.issue(agent.agent_id)
        iam.credentials.revoke(cred.credential_id)
        assert cred.is_valid is False

    def test_time_remaining_positive(self, iam, agent):
        cred = iam.credentials.issue(agent.agent_id, ttl=300)
        assert cred.time_remaining() > 0

    def test_time_remaining_negative_when_expired(self, iam, agent):
        cred = iam.credentials.issue(agent.agent_id, ttl=0)
        import time
        time.sleep(0.1)
        assert cred.time_remaining() < 0
