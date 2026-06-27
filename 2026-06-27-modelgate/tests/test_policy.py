"""Tests for ModelGate policy engine."""

from datetime import datetime, timezone, timedelta

import pytest

from modelgate.models import AccessStatus, ModelTier
from modelgate.policy import (
    JUSTIFICATION_MIN_LENGTH,
    PolicyEngine,
)
from modelgate.store import ModelGateStore


@pytest.fixture
def store(tmp_path):
    """Create a temporary store for testing."""
    db_path = str(tmp_path / "test_policy.db")
    s = ModelGateStore(db_path)
    yield s
    s.close()


@pytest.fixture
def policy(store):
    return PolicyEngine(store)


class TestCheckAccess:
    def test_allowed_with_grant(self, store, policy):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        store.register_model("gpt-4o", "OpenAI", ModelTier.RESTRICTED)
        store.grant_access("alice@test.com", ModelTier.RESTRICTED, "Need restricted", "boss@test.com")

        result = policy.check_access("alice@test.com", "gpt-4o")
        assert result.allowed is True
        assert "active" in result.reason.lower() or "granted" in result.reason.lower()

    def test_denied_without_grant(self, store, policy):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        store.register_model("gpt-5.6", "OpenAI", ModelTier.CLASSIFIED)

        result = policy.check_access("alice@test.com", "gpt-5.6")
        assert result.allowed is False
        assert "classified" in result.reason.lower()

    def test_denied_model_not_found(self, store, policy):
        result = policy.check_access("alice@test.com", "nonexistent-model")
        assert result.allowed is False
        assert "not found" in result.reason.lower()

    def test_denied_expired_grant(self, store, policy):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        store.register_model("gpt-4o", "OpenAI", ModelTier.RESTRICTED)
        past = datetime.now(timezone.utc) - timedelta(days=1)
        grant = store.grant_access(
            "alice@test.com", ModelTier.RESTRICTED, "Need restricted",
            "boss@test.com", expires_at=past,
        )
        # The grant is still ACTIVE in DB but expired timestamp
        # Policy engine should check expiry
        result = policy.check_access("alice@test.com", "gpt-4o")
        assert result.allowed is False
        assert "expired" in result.reason.lower()


class TestValidateGrantRequest:
    def test_valid_request(self, store, policy):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        error = policy.validate_grant_request(
            "alice@test.com", ModelTier.RESTRICTED,
            "Need restricted access for project",
            "boss@test.com",
        )
        assert error is None

    def test_employee_not_found(self, store, policy):
        error = policy.validate_grant_request(
            "nobody@test.com", ModelTier.RESTRICTED,
            "Some justification text here",
            "boss@test.com",
        )
        assert error is not None
        assert "not found" in error.lower()

    def test_justification_too_short(self, store, policy):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        # CLASSIFIED tier requires >= 20 chars
        error = policy.validate_grant_request(
            "alice@test.com", ModelTier.CLASSIFIED,
            "Too short",
            "boss@test.com",
        )
        assert error is not None
        assert "justification" in error.lower() or "characters" in error.lower()

    def test_missing_approver_for_restricted(self, store, policy):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        error = policy.validate_grant_request(
            "alice@test.com", ModelTier.RESTRICTED,
            "Valid justification text here",
            "",  # No approver
        )
        assert error is not None
        assert "approver" in error.lower()

    def test_already_has_access(self, store, policy):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        store.grant_access("alice@test.com", ModelTier.RESTRICTED, "Need restricted", "boss@test.com")

        error = policy.validate_grant_request(
            "alice@test.com", ModelTier.RESTRICTED,
            "Want restricted access for project work",
            "boss@test.com",
        )
        assert error is not None
        assert "already" in error.lower()

    def test_government_vetted_requires_long_justification(self, store, policy):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        min_len = JUSTIFICATION_MIN_LENGTH[ModelTier.GOVERNMENT_VETTED]
        short_text = "x" * (min_len - 1)
        error = policy.validate_grant_request(
            "alice@test.com", ModelTier.GOVERNMENT_VETTED,
            short_text,
            "ciso@test.com",
        )
        assert error is not None


class TestEmployeeTierSummary:
    def test_summary(self, store, policy):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        store.grant_access("alice@test.com", ModelTier.RESTRICTED, "Need restricted", "boss@test.com")

        summary = policy.employee_tier_summary("alice@test.com")
        assert summary[ModelTier.PUBLIC] is False  # Don't auto-grant lower tiers
        assert summary[ModelTier.RESTRICTED] is True
        assert summary[ModelTier.CLASSIFIED] is False
        assert summary[ModelTier.GOVERNMENT_VETTED] is False

    def test_empty_summary(self, store, policy):
        store.add_employee("alice@test.com", "Alice", "Engineering")
        summary = policy.employee_tier_summary("alice@test.com")
        assert all(v is False for v in summary.values())
