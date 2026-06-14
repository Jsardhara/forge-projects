"""Tests for RegShield models."""

from regshield.models import (
    AIModel,
    ComplianceCheckRequest,
    ComplianceCheckResult,
    Jurisdiction,
    ModelProvider,
    RegulatoryStatus,
    RiskLevel,
    UseCase,
)


class TestAIModel:
    def test_create_model(self):
        m = AIModel(
            model_id="openai/gpt-4o",
            name="GPT-4o",
            provider=ModelProvider.OPENAI,
        )
        assert m.model_id == "openai/gpt-4o"
        assert m.name == "GPT-4o"
        assert m.provider == ModelProvider.OPENAI
        assert m.version == "latest"

    def test_model_with_capabilities(self):
        m = AIModel(
            model_id="test/model",
            name="Test Model",
            provider=ModelProvider.OTHER,
            capabilities=["text", "code"],
        )
        assert len(m.capabilities) == 2

    def test_model_serialization(self):
        m = AIModel(
            model_id="openai/gpt-4o",
            name="GPT-4o",
            provider=ModelProvider.OPENAI,
        )
        d = m.model_dump()
        assert d["model_id"] == "openai/gpt-4o"
        assert d["provider"] == "openai"


class TestRegulatoryStatus:
    def test_create_status(self):
        s = RegulatoryStatus(
            model_id="anthropic/claude-fable-5",
            jurisdiction=Jurisdiction.US,
            risk_level=RiskLevel.BANNED,
        )
        assert s.model_id == "anthropic/claude-fable-5"
        assert s.jurisdiction == Jurisdiction.US
        assert s.risk_level == RiskLevel.BANNED

    def test_status_with_restrictions(self):
        s = RegulatoryStatus(
            model_id="test/model",
            jurisdiction=Jurisdiction.US,
            risk_level=RiskLevel.RESTRICTED,
            restrictions=["Gov use banned", "Export control"],
        )
        assert len(s.restrictions) == 2


class TestComplianceCheckRequest:
    def test_basic_request(self):
        r = ComplianceCheckRequest(
            model_id="openai/gpt-4o",
            jurisdiction=Jurisdiction.US,
        )
        assert r.use_case == UseCase.GENERAL

    def test_request_with_use_case(self):
        r = ComplianceCheckRequest(
            model_id="deepseek/deepseek-v3",
            jurisdiction=Jurisdiction.US,
            use_case=UseCase.GOVERNMENT,
        )
        assert r.use_case == UseCase.GOVERNMENT


class TestComplianceCheckResult:
    def test_allowed_result(self):
        r = ComplianceCheckResult(
            model_id="openai/gpt-4o",
            model_name="GPT-4o",
            jurisdiction=Jurisdiction.US,
            use_case=UseCase.GENERAL,
            risk_level=RiskLevel.COMPLIANT,
            is_allowed=True,
        )
        assert r.is_allowed is True

    def test_banned_result(self):
        r = ComplianceCheckResult(
            model_id="anthropic/claude-fable-5",
            model_name="Claude Fable 5",
            jurisdiction=Jurisdiction.US,
            use_case=UseCase.GENERAL,
            risk_level=RiskLevel.BANNED,
            is_allowed=False,
        )
        assert r.is_allowed is False


class TestEnums:
    def test_risk_levels(self):
        assert RiskLevel.COMPLIANT.value == "compliant"
        assert RiskLevel.BANNED.value == "banned"
        assert RiskLevel.PENDING_REVIEW.value == "pending_review"

    def test_jurisdictions(self):
        assert Jurisdiction.US.value == "US"
        assert Jurisdiction.EU.value == "EU"
        assert Jurisdiction.CN.value == "CN"

    def test_use_cases(self):
        assert UseCase.GENERAL.value == "general"
        assert UseCase.GOVERNMENT.value == "government"
        assert UseCase.DEFENSE.value == "defense"
