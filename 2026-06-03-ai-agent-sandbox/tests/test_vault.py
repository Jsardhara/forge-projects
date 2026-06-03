"""Tests for the API Key Vault."""
import os
import pytest
from ai_agent_sandbox.vault import ApiKeyVault, KeyScope, VaultError, PermissionDenied


@pytest.fixture
def env_with_keys():
    os.environ["TEST_OPENAI_KEY"] = "***"
    os.environ["TEST_ANTHROPIC_KEY"] = "sk-ant-67890"
    os.environ["TEST_WEAK_KEY"] = "sk_weak_123"
    yield
    for key in ("TEST_OPENAI_KEY", "TEST_ANTHROPIC_KEY", "TEST_WEAK_KEY"):
        os.environ.pop(key, None)


class TestKeyScope:
    def test_allows_all_when_empty(self):
        scope = KeyScope()
        assert scope.allows_model("any-model")
        assert scope.allows_endpoint("/v1/anything")

    def test_allows_specific_model(self):
        scope = KeyScope(allowed_models=("gpt-4", "gpt-3.5-turbo"))
        assert scope.allows_model("gpt-4")
        assert not scope.allows_model("claude-3")

    def test_allows_specific_endpoint(self):
        scope = KeyScope(allowed_endpoints=("/v1/chat/completions",))
        assert scope.allows_endpoint("/v1/chat/completions")
        assert not scope.allows_endpoint("/v1/embeddings")


class TestApiKeyVault:
    def test_load_from_env_success(self, env_with_keys):
        vault = ApiKeyVault()
        name = vault.load_from_env("TEST_OPENAI_KEY", name="openai")
        assert name == "openai"
        assert vault.key_count == 1

    def test_load_from_env_missing_raises(self):
        vault = ApiKeyVault()
        with pytest.raises(VaultError, match="not set"):
            vault.load_from_env("NONEXISTENT_KEY_XYZ_12345")

    def test_permission_granted(self, env_with_keys):
        vault = ApiKeyVault()
        vault.load_from_env("TEST_OPENAI_KEY", name="openai")
        assert vault.check_permission("openai", model="gpt-4") is True

    def test_permission_denied_for_model(self, env_with_keys):
        vault = ApiKeyVault()
        vault.load_from_env(
            "TEST_OPENAI_KEY",
            name="openai",
            scope=KeyScope(allowed_models=("gpt-4",)),
        )
        with pytest.raises(PermissionDenied):
            vault.check_permission("openai", model="claude-3")

    def test_permission_denied_for_endpoint(self, env_with_keys):
        vault = ApiKeyVault()
        vault.load_from_env(
            "TEST_OPENAI_KEY",
            name="openai",
            scope=KeyScope(allowed_endpoints=("/v1/chat/completions",)),
        )
        with pytest.raises(PermissionDenied):
            vault.check_permission("openai", endpoint="/v1/embeddings")

    def test_key_not_found(self):
        vault = ApiKeyVault()
        with pytest.raises(VaultError, match="not found"):
            vault.check_permission("nonexistent")

    def test_usage_tracking(self, env_with_keys):
        vault = ApiKeyVault()
        vault.load_from_env("TEST_OPENAI_KEY", name="openai")
        vault.check_permission("openai", tokens=100)
        vault.check_permission("openai", tokens=200)
        usage = vault.get_usage("openai")
        assert usage["request_count"] == 2
        assert usage["token_count"] == 300

    def test_audit_log(self, env_with_keys):
        vault = ApiKeyVault()
        vault.load_from_env("TEST_OPENAI_KEY", name="openai")
        vault.check_permission("openai", model="gpt-4")
        log = vault.get_audit_log()
        assert len(log) >= 2  # key_loaded + permission_granted
        assert log[0]["event"] == "key_loaded"

    def test_multiple_keys(self, env_with_keys):
        vault = ApiKeyVault()
        vault.load_from_env("TEST_OPENAI_KEY", name="openai")
        vault.load_from_env("TEST_ANTHROPIC_KEY", name="anthropic")
        assert vault.key_count == 2
