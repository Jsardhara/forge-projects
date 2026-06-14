"""Tests for RegShield store."""

import pytest

from regshield.models import Jurisdiction, RiskLevel, UseCase
from regshield.store import RegShieldStore


@pytest.fixture
def store():
    return RegShieldStore()


class TestModelRegistry:
    def test_list_models(self, store):
        models = store.list_models()
        assert len(models) > 0

    def test_get_known_model(self, store):
        m = store.get_model("openai/gpt-4o")
        assert m is not None
        assert m.name == "GPT-4o"

    def test_get_unknown_model(self, store):
        m = store.get_model("nonexistent/model")
        assert m is None

    def test_add_model(self, store):
        from regshield.models import AIModel, ModelProvider
        new_model = AIModel(
            model_id="test/new-model",
            name="New Model",
            provider=ModelProvider.OTHER,
        )
        store.add_model(new_model)
        retrieved = store.get_model("test/new-model")
        assert retrieved is not None
        assert retrieved.name == "New Model"


class TestComplianceCheck:
    def test_compliant_model(self, store):
        # Gemini 2.5 Pro is fully compliant in US
        result = store.check_compliance(
            "google/gemini-2.5-pro", Jurisdiction.US, UseCase.GENERAL
        )
        assert result is not None
        assert result.risk_level == RiskLevel.COMPLIANT
        assert result.is_allowed is True

    def test_banned_model(self, store):
        result = store.check_compliance(
            "anthropic/claude-fable-5", Jurisdiction.US, UseCase.GENERAL
        )
        assert result is not None
        assert result.risk_level == RiskLevel.BANNED
        assert result.is_allowed is False

    def test_pending_review_model(self, store):
        result = store.check_compliance(
            "openai/gpt-4o", Jurisdiction.US, UseCase.GENERAL
        )
        # GPT-4o is PENDING_REVIEW in US due to AG investigation
        assert result is not None

    def test_unknown_model_returns_none(self, store):
        result = store.check_compliance(
            "nonexistent/model", Jurisdiction.US, UseCase.GENERAL
        )
        assert result is None

    def test_unknown_jurisdiction_returns_unknown(self, store):
        result = store.check_compliance(
            "openai/gpt-4o", Jurisdiction.JP, UseCase.GENERAL
        )
        assert result is not None
        assert result.risk_level == RiskLevel.UNKNOWN

    def test_chinese_model_gov_restricted(self, store):
        result = store.check_compliance(
            "deepseek/deepseek-v3", Jurisdiction.US, UseCase.GOVERNMENT
        )
        assert result is not None
        assert result.risk_level == RiskLevel.RESTRICTED

    def test_chinese_model_general_compliant(self, store):
        result = store.check_compliance(
            "deepseek/deepseek-v3", Jurisdiction.US, UseCase.GENERAL
        )
        assert result is not None
        assert result.risk_level == RiskLevel.COMPLIANT

    def test_india_fable_banned(self, store):
        result = store.check_compliance(
            "anthropic/claude-fable-5", Jurisdiction.IN, UseCase.GENERAL
        )
        assert result is not None
        assert result.risk_level == RiskLevel.BANNED
        assert result.is_allowed is False


class TestAlerts:
    def test_list_alerts(self, store):
        alerts = store.list_alerts()
        assert len(alerts) > 0

    def test_unread_alerts(self, store):
        unread = store.list_alerts(unread_only=True)
        assert len(unread) > 0

    def test_acknowledge_alert(self, store):
        alerts = store.list_alerts(unread_only=True)
        if alerts:
            alert_id = alerts[0].alert_id
            assert store.acknowledge_alert(alert_id) is True
            # Should no longer be in unread
            unread = store.list_alerts(unread_only=True)
            assert all(a.alert_id != alert_id for a in unread)

    def test_acknowledge_nonexistent(self, store):
        assert store.acknowledge_alert("NONEXISTENT") is False


class TestAuditLog:
    def test_audit_after_check(self, store):
        initial_count = len(store.list_audit_log())
        store.check_compliance("openai/gpt-4o", Jurisdiction.US, UseCase.GENERAL)
        new_count = len(store.list_audit_log())
        assert new_count == initial_count + 1

    def test_audit_limit(self, store):
        entries = store.list_audit_log(limit=5)
        assert len(entries) <= 5


class TestStatusFiltering:
    def test_filter_by_jurisdiction(self, store):
        us_statuses = store.list_statuses(jurisdiction=Jurisdiction.US)
        assert len(us_statuses) > 0
        assert all(s.jurisdiction == Jurisdiction.US for s in us_statuses)

    def test_filter_by_risk_level(self, store):
        banned = store.list_statuses(risk_level=RiskLevel.BANNED)
        assert len(banned) > 0
        assert all(s.risk_level == RiskLevel.BANNED for s in banned)

    def test_combined_filter(self, store):
        us_banned = store.list_statuses(
            jurisdiction=Jurisdiction.US, risk_level=RiskLevel.BANNED
        )
        assert all(
            s.jurisdiction == Jurisdiction.US and s.risk_level == RiskLevel.BANNED
            for s in us_banned
        )
