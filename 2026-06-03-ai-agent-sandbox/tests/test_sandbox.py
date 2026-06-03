"""Tests for the main Sandbox orchestrator."""
import os
import pytest
from ai_agent_sandbox.sandbox import Sandbox, SandboxConfig
from ai_agent_sandbox.vault import KeyScope, PermissionDenied


@pytest.fixture
def env_with_keys():
    """Provide environment with test API keys set."""
    os.environ["SB_OPENAI_KEY"] = "***"
    os.environ["SB_ANTHROPIC_KEY"] = "***"
    yield
    os.environ.pop("SB_OPENAI_KEY", None)
    os.environ.pop("SB_ANTHROPIC_KEY", None)


class TestSandbox:
    def test_create_default(self):
        sb = Sandbox()
        assert sb.is_killed is False
        assert sb.vault.key_count == 0

    def test_create_with_config(self):
        sb = Sandbox(SandboxConfig(
            agent_id="agent-1",
            allowed_domains=["api.openai.com"],
            allowed_dirs=["/home/user/projects"],
        ))
        assert "api.openai.com" in sb.network.get_allowed_domains()

    def test_load_key(self, env_with_keys):
        sb = Sandbox(SandboxConfig(agent_id="test"))
        sb.load_key("SB_OPENAI_KEY", name="openai")
        assert sb.vault.key_count == 1

    def test_network_check(self):
        sb = Sandbox(SandboxConfig(
            agent_id="test",
            allowed_domains=["api.openai.com"],
        ))
        assert sb.check_network("https://api.openai.com/v1/chat") is True
        assert sb.check_network("https://evil.com/steal") is False

    def test_kill_switch(self):
        sb = Sandbox(SandboxConfig(
            agent_id="test",
            allowed_domains=["api.openai.com"],
        ))
        assert sb.check_network("https://api.openai.com/v1/chat") is True
        sb.kill()
        assert sb.is_killed is True
        assert sb.check_network("https://api.openai.com/v1/chat") is False

    def test_resume(self):
        sb = Sandbox(SandboxConfig(
            agent_id="test",
            allowed_domains=["api.openai.com"],
        ))
        sb.kill()
        sb.resume()
        assert sb.is_killed is False
        assert sb.check_network("https://api.openai.com/v1/chat") is True

    def test_key_permission_denied(self, env_with_keys):
        sb = Sandbox(SandboxConfig(agent_id="test"))
        sb.load_key("SB_OPENAI_KEY", name="openai", scope=KeyScope(allowed_models=("gpt-4",)))
        with pytest.raises(PermissionDenied):
            sb.check_key("openai", model="claude-3")

    def test_audit_summary(self, env_with_keys):
        sb = Sandbox(SandboxConfig(
            agent_id="test",
            allowed_domains=["api.openai.com"],
        ))
        sb.load_key("SB_OPENAI_KEY", name="openai")
        sb.check_network("https://api.openai.com/v1/chat")
        sb.check_network("https://evil.com")
        summary = sb.audit_summary()
        assert summary["agent_id"] == "test"
        assert summary["keys_loaded"] == 1
        assert summary["audit"]["violations"] >= 1
