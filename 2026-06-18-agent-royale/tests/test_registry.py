"""Tests for IdentityRegistry and Agent model."""

import pytest
from agent_royale import Agent, AgentStatus, IdentityRegistry


class TestAgent:
    def test_create_agent(self):
        agent = Agent(name="TestBot", model_id="openai/gpt-4o")
        assert agent.name == "TestBot"
        assert agent.model_id == "openai/gpt-4o"
        assert agent.status == AgentStatus.REGISTERED
        assert agent.score == 0.0
        assert agent.wins == 0
        assert agent.losses == 0
        assert len(agent.agent_id) == 8

    def test_agent_id_unique(self):
        a1 = Agent(name="A1", model_id="model/a")
        a2 = Agent(name="A2", model_id="model/b")
        assert a1.agent_id != a2.agent_id

    def test_win_rate_no_games(self):
        agent = Agent(name="Test", model_id="model/x")
        assert agent.win_rate == 0.0

    def test_win_rate_with_wins(self):
        agent = Agent(name="Test", model_id="model/x", wins=3, losses=1)
        assert agent.win_rate == 0.75

    def test_win_rate_all_wins(self):
        agent = Agent(name="Test", model_id="model/x", wins=5, losses=0)
        assert agent.win_rate == 1.0

    def test_to_dict(self):
        agent = Agent(name="DictBot", model_id="model/z")
        d = agent.to_dict()
        assert d["name"] == "DictBot"
        assert d["model_id"] == "model/z"
        assert d["status"] == "registered"
        assert "agent_id" in d
        assert "win_rate" in d


class TestIdentityRegistry:
    def test_register_agent(self):
        reg = IdentityRegistry()
        agent = reg.register("Bot1", "openai/gpt-4o")
        assert reg.count() == 1
        assert agent.name == "Bot1"

    def test_register_multiple(self):
        reg = IdentityRegistry()
        reg.register("A", "model/a")
        reg.register("B", "model/b")
        reg.register("C", "model/c")
        assert reg.count() == 3

    def test_get_agent(self):
        reg = IdentityRegistry()
        agent = reg.register("FindMe", "model/x")
        found = reg.get(agent.agent_id)
        assert found is not None
        assert found.name == "FindMe"

    def test_get_nonexistent(self):
        reg = IdentityRegistry()
        assert reg.get("nonexistent") is None

    def test_list_all(self):
        reg = IdentityRegistry()
        reg.register("A", "model/a")
        reg.register("B", "model/b")
        agents = reg.list_all()
        assert len(agents) == 2

    def test_list_active(self):
        reg = IdentityRegistry()
        a1 = reg.register("Active", "model/a")
        a2 = reg.register("Inactive", "model/b")
        reg.update_status(a2.agent_id, AgentStatus.ELIMINATED)
        active = reg.list_active()
        assert len(active) == 1
        assert active[0].name == "Active"

    def test_update_status(self):
        reg = IdentityRegistry()
        agent = reg.register("StatusBot", "model/x")
        reg.update_status(agent.agent_id, AgentStatus.PLAYING)
        updated = reg.get(agent.agent_id)
        assert updated.status == AgentStatus.PLAYING

    def test_remove_agent(self):
        reg = IdentityRegistry()
        agent = reg.register("Goner", "model/x")
        assert reg.remove(agent.agent_id) is True
        assert reg.count() == 0

    def test_remove_nonexistent(self):
        reg = IdentityRegistry()
        assert reg.remove("fake-id") is False
