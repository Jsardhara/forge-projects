"""Tests for AgentIAM — Identity Registry."""

import pytest
from agentiam import AgentIAM, AgentIdentity, AgentStatus, IdentityRegistry


@pytest.fixture
def registry():
    return IdentityRegistry()


@pytest.fixture
def iam():
    return AgentIAM()


class TestRegister:
    def test_register_basic(self, registry):
        agent = registry.register(name="test-agent", owner="alice")
        assert agent.name == "test-agent"
        assert agent.owner == "alice"
        assert agent.agent_id.startswith("agent-")
        assert agent.status == AgentStatus.ACTIVE

    def test_register_with_all_fields(self, registry):
        agent = registry.register(
            name="travel-bot",
            owner="platform-team",
            description="Books flights",
            code_hash="sha256:abc123",
            model_id="openai/gpt-4o",
            scopes=["travel:read", "travel:book"],
            metadata={"env": "prod"},
        )
        assert agent.description == "Books flights"
        assert agent.code_hash == "sha256:abc123"
        assert agent.model_id == "openai/gpt-4o"
        assert agent.scopes == ["travel:read", "travel:book"]
        assert agent.metadata["env"] == "prod"

    def test_register_requires_name(self, registry):
        with pytest.raises(ValueError, match="name is required"):
            registry.register(name="", owner="alice")

    def test_register_requires_owner(self, registry):
        with pytest.raises(ValueError, match="owner is required"):
            registry.register(name="test", owner="")

    def test_register_generates_unique_ids(self, registry):
        a1 = registry.register(name="a1", owner="alice")
        a2 = registry.register(name="a2", owner="alice")
        assert a1.agent_id != a2.agent_id


class TestGet:
    def test_get_existing(self, registry):
        agent = registry.register(name="test", owner="alice")
        found = registry.get(agent.agent_id)
        assert found is not None
        assert found.agent_id == agent.agent_id

    def test_get_missing(self, registry):
        assert registry.get("agent-nonexistent") is None


class TestListAgents:
    def test_list_all(self, registry):
        registry.register(name="a1", owner="alice")
        registry.register(name="a2", owner="bob")
        assert len(registry.list_agents()) == 2

    def test_list_by_status(self, registry):
        a1 = registry.register(name="a1", owner="alice")
        registry.register(name="a2", owner="bob")
        registry.suspend(a1.agent_id)
        active = registry.list_agents(status=AgentStatus.ACTIVE)
        suspended = registry.list_agents(status=AgentStatus.SUSPENDED)
        assert len(active) == 1
        assert len(suspended) == 1


class TestSuspendRevoke:
    def test_suspend(self, registry):
        agent = registry.register(name="test", owner="alice")
        result = registry.suspend(agent.agent_id)
        assert result.status == AgentStatus.SUSPENDED
        assert not result.is_active

    def test_revoke(self, registry):
        agent = registry.register(name="test", owner="alice")
        result = registry.revoke(agent.agent_id)
        assert result.status == AgentStatus.REVOKED

    def test_suspend_missing_raises(self, registry):
        with pytest.raises(KeyError):
            registry.suspend("agent-nonexistent")

    def test_revoke_missing_raises(self, registry):
        with pytest.raises(KeyError):
            registry.revoke("agent-nonexistent")


class TestFingerprint:
    def test_fingerprint_deterministic(self, registry):
        agent = registry.register(name="test", owner="alice", code_hash="abc")
        fp1 = agent.fingerprint()
        fp2 = agent.fingerprint()
        assert fp1 == fp2
        assert len(fp1) == 12

    def test_fingerprint_differs(self, registry):
        a1 = registry.register(name="a1", owner="alice", code_hash="abc")
        a2 = registry.register(name="a2", owner="alice", code_hash="xyz")
        assert a1.fingerprint() != a2.fingerprint()


class TestUpdateCodeHash:
    def test_update(self, registry):
        agent = registry.register(name="test", owner="alice", code_hash="old")
        updated = registry.update_code_hash(agent.agent_id, "sha256:newhash")
        assert updated.code_hash == "sha256:newhash"

    def test_update_missing_raises(self, registry):
        with pytest.raises(KeyError):
            registry.update_code_hash("agent-nonexistent", "hash")


class TestCount:
    def test_count_empty(self, registry):
        assert registry.count() == 0

    def test_count_after_register(self, registry):
        registry.register(name="a1", owner="alice")
        registry.register(name="a2", owner="bob")
        assert registry.count() == 2
