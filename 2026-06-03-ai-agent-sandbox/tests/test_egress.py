"""Tests for the Network Egress Controller."""
import pytest
from ai_agent_sandbox.egress import NetworkEgressController


class TestNetworkEgressController:
    def test_default_deny_blocks_unknown(self):
        ctrl = NetworkEgressController(default_deny=True)
        assert ctrl.check_access("https://evil.com/steal") is False

    def test_allowlist_permits_matching(self):
        ctrl = NetworkEgressController(default_deny=True)
        ctrl.allow_domain("api.openai.com")
        assert ctrl.check_access("https://api.openai.com/v1/chat") is True

    def test_allowlist_blocks_non_matching(self):
        ctrl = NetworkEgressController(default_deny=True)
        ctrl.allow_domain("api.openai.com")
        assert ctrl.check_access("https://api.anthropic.com/v1/messages") is False

    def test_deny_domain_removes_from_allowlist(self):
        ctrl = NetworkEgressController(default_deny=True)
        ctrl.allow_domain("api.openai.com")
        ctrl.deny_domain("api.openai.com")
        assert ctrl.check_access("https://api.openai.com/v1/chat") is False

    def test_kill_switch_blocks_all(self):
        ctrl = NetworkEgressController(default_deny=True)
        ctrl.allow_domain("api.openai.com")
        assert ctrl.check_access("https://api.openai.com/v1/chat") is True
        ctrl.activate_kill_switch()
        assert ctrl.check_access("https://api.openai.com/v1/chat") is False
        assert ctrl.is_kill_switch_active is True

    def test_resume_after_kill_switch(self):
        ctrl = NetworkEgressController(default_deny=True)
        ctrl.allow_domain("api.openai.com")
        ctrl.activate_kill_switch()
        ctrl.deactivate_kill_switch()
        assert ctrl.is_kill_switch_active is False
        assert ctrl.check_access("https://api.openai.com/v1/chat") is True

    def test_event_logging(self):
        ctrl = NetworkEgressController(default_deny=True)
        ctrl.allow_domain("api.openai.com")
        ctrl.check_access("https://api.openai.com/v1/chat")
        ctrl.check_access("https://evil.com/steal")
        events = ctrl.get_events()
        assert len(events) == 2
        assert events[0].allowed is True
        assert events[1].allowed is False

    def test_blocked_count(self):
        ctrl = NetworkEgressController(default_deny=True)
        ctrl.allow_domain("api.openai.com")
        ctrl.check_access("https://api.openai.com/v1/chat")
        ctrl.check_access("https://evil.com/steal")
        ctrl.check_access("https://bad.com/data")
        assert ctrl.get_blocked_count() == 2

    def test_allowed_domains_list(self):
        ctrl = NetworkEgressController()
        ctrl.allow_domain("api.openai.com")
        ctrl.allow_domain("api.anthropic.com")
        domains = ctrl.get_allowed_domains()
        assert "api.openai.com" in domains
        assert "api.anthropic.com" in domains

    def test_filter_events_by_agent(self):
        ctrl = NetworkEgressController(default_deny=True)
        ctrl.check_access("https://evil.com", agent_id="agent-1")
        ctrl.check_access("https://evil.com", agent_id="agent-2")
        events = ctrl.get_events(agent_id="agent-1")
        assert len(events) == 1
        assert events[0].agent_id == "agent-1"
