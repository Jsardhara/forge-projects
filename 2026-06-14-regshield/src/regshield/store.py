"""In-memory data store for RegShield.

In production this would be PostgreSQL. For the MVP we use
a thread-safe in-memory store with seed data reflecting
real regulatory events from June 2026.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from regshield.models import (
    AIModel,
    Alert,
    AuditEntry,
    ComplianceCheckResult,
    Jurisdiction,
    ModelProvider,
    RegulatoryStatus,
    RiskLevel,
    UseCase,
)


class RegShieldStore:
    """Thread-safe in-memory store for all RegShield data."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._models: dict[str, AIModel] = {}
        self._statuses: list[RegulatoryStatus] = []
        self._alerts: list[Alert] = []
        self._audit_log: list[AuditEntry] = []
        self._seed_data()

    # -- Models --

    def get_model(self, model_id: str) -> Optional[AIModel]:
        with self._lock:
            return self._models.get(model_id)

    def list_models(self) -> list[AIModel]:
        with self._lock:
            return list(self._models.values())

    def add_model(self, model: AIModel) -> AIModel:
        with self._lock:
            self._models[model.model_id] = model
            return model

    # -- Regulatory Statuses --

    def get_status(
        self, model_id: str, jurisdiction: Jurisdiction, use_case: UseCase
    ) -> Optional[RegulatoryStatus]:
        with self._lock:
            for s in self._statuses:
                if (
                    s.model_id == model_id
                    and s.jurisdiction == jurisdiction
                    and s.use_case == use_case
                ):
                    return s
            # Fall back to GENERAL use case if specific one not found
            if use_case != UseCase.GENERAL:
                for s in self._statuses:
                    if (
                        s.model_id == model_id
                        and s.jurisdiction == jurisdiction
                        and s.use_case == UseCase.GENERAL
                    ):
                        return s
            return None

    def list_statuses(
        self,
        jurisdiction: Optional[Jurisdiction] = None,
        risk_level: Optional[RiskLevel] = None,
    ) -> list[RegulatoryStatus]:
        with self._lock:
            results = list(self._statuses)
            if jurisdiction:
                results = [s for s in results if s.jurisdiction == jurisdiction]
            if risk_level:
                results = [s for s in results if s.risk_level == risk_level]
            return results

    def add_status(self, status: RegulatoryStatus) -> RegulatoryStatus:
        with self._lock:
            self._statuses.append(status)
            return status

    # -- Compliance Check --

    def check_compliance(
        self, model_id: str, jurisdiction: Jurisdiction, use_case: UseCase
    ) -> Optional[ComplianceCheckResult]:
        model = self.get_model(model_id)
        if not model:
            return None

        status = self.get_status(model_id, jurisdiction, use_case)
        if not status:
            return ComplianceCheckResult(
                model_id=model_id,
                model_name=model.name,
                jurisdiction=jurisdiction,
                use_case=use_case,
                risk_level=RiskLevel.UNKNOWN,
                is_allowed=True,
                restrictions=[],
                notes="No regulatory data available for this model/jurisdiction combination.",
            )

        is_allowed = status.risk_level in (
            RiskLevel.COMPLIANT,
            RiskLevel.PENDING_REVIEW,
        )

        result = ComplianceCheckResult(
            model_id=model_id,
            model_name=model.name,
            jurisdiction=jurisdiction,
            use_case=use_case,
            risk_level=status.risk_level,
            is_allowed=is_allowed,
            restrictions=status.restrictions,
            source_url=status.source_url,
            notes=status.notes,
        )

        # Audit the check
        self._audit(
            action="compliance_check",
            model_id=model_id,
            jurisdiction=jurisdiction,
            use_case=use_case,
            result=status.risk_level,
        )

        return result

    # -- Alerts --

    def list_alerts(self, unread_only: bool = False) -> list[Alert]:
        with self._lock:
            alerts = list(self._alerts)
            if unread_only:
                alerts = [a for a in alerts if not a.acknowledged]
            return alerts

    def add_alert(self, alert: Alert) -> Alert:
        with self._lock:
            self._alerts.append(alert)
            return alert

    def acknowledge_alert(self, alert_id: str) -> bool:
        with self._lock:
            for a in self._alerts:
                if a.alert_id == alert_id:
                    a.acknowledged = True
                    return True
            return False

    # -- Audit Log --

    def list_audit_log(self, limit: int = 100) -> list[AuditEntry]:
        with self._lock:
            return list(reversed(self._audit_log[-limit:]))

    def _audit(
        self,
        action: str,
        model_id: str,
        jurisdiction: Jurisdiction,
        use_case: UseCase,
        result: RiskLevel,
        details: str = "",
    ) -> None:
        entry = AuditEntry(
            entry_id=str(uuid.uuid4())[:8],
            action=action,
            model_id=model_id,
            jurisdiction=jurisdiction,
            use_case=use_case,
            result=result,
            timestamp=datetime.now(timezone.utc),
            details=details,
        )
        self._audit_log.append(entry)

    # -- Seed Data --

    def _seed_data(self) -> None:
        """Seed with real regulatory data from June 2026."""

        models = [
            AIModel(
                model_id="openai/gpt-4o",
                name="GPT-4o",
                provider=ModelProvider.OPENAI,
                version="4o",
                release_date="2024-05-13",
                capabilities=["text", "vision", "code", "function_calling"],
            ),
            AIModel(
                model_id="openai/o3",
                name="o3",
                provider=ModelProvider.OPENAI,
                version="o3",
                release_date="2025-04-16",
                capabilities=["reasoning", "code", "math", "science"],
            ),
            AIModel(
                model_id="openai/gpt-5",
                name="GPT-5",
                provider=ModelProvider.OPENAI,
                version="5",
                release_date="2025-08-07",
                capabilities=["text", "vision", "code", "reasoning", "multimodal"],
            ),
            AIModel(
                model_id="anthropic/claude-sonnet-4",
                name="Claude Sonnet 4",
                provider=ModelProvider.ANTHROPIC,
                version="4",
                release_date="2025-05-22",
                capabilities=["text", "code", "vision", "analysis"],
            ),
            AIModel(
                model_id="anthropic/claude-opus-4",
                name="Claude Opus 4",
                provider=ModelProvider.ANTHROPIC,
                version="4",
                release_date="2025-05-22",
                capabilities=["text", "code", "vision", "reasoning", "analysis"],
            ),
            AIModel(
                model_id="anthropic/claude-3.5-sonnet",
                name="Claude 3.5 Sonnet",
                provider=ModelProvider.ANTHROPIC,
                version="3.5",
                release_date="2024-06-20",
                capabilities=["text", "code", "vision"],
            ),
            AIModel(
                model_id="google/gemini-2.5-pro",
                name="Gemini 2.5 Pro",
                provider=ModelProvider.GOOGLE,
                version="2.5",
                release_date="2025-03-25",
                capabilities=["text", "vision", "code", "reasoning", "multimodal"],
            ),
            AIModel(
                model_id="google/gemini-2.5-flash",
                name="Gemini 2.5 Flash",
                provider=ModelProvider.GOOGLE,
                version="2.5",
                release_date="2025-06-17",
                capabilities=["text", "vision", "code", "fast_inference"],
            ),
            AIModel(
                model_id="meta/llama-4-maverick",
                name="Llama 4 Maverick",
                provider=ModelProvider.META,
                version="4",
                release_date="2025-04-05",
                capabilities=["text", "vision", "code", "open_weights"],
                notes="Open weights model. Meta unwound $2B Manus deal after Beijing demands.",
            ),
            AIModel(
                model_id="deepseek/deepseek-v3",
                name="DeepSeek V3",
                provider=ModelProvider.DEEPSEEK,
                version="3",
                release_date="2024-12-26",
                capabilities=["text", "code", "reasoning", "open_weights"],
                notes="Chinese model. Open weights. Competitive with GPT-4o.",
            ),
            AIModel(
                model_id="deepseek/deepseek-r1",
                name="DeepSeek R1",
                provider=ModelProvider.DEEPSEEK,
                version="r1",
                release_date="2025-01-20",
                capabilities=["reasoning", "math", "science", "open_weights"],
                notes="Chinese model. Reasoning-focused. Open weights.",
            ),
            AIModel(
                model_id="zai/glm-5.2",
                name="GLM 5.2",
                provider=ModelProvider.ZAI,
                version="5.2",
                release_date="2026-06-13",
                capabilities=["text", "code", "reasoning", "multilingual"],
                notes="Chinese frontier model. 581pts on HN. Competitive with GPT-4o.",
            ),
            AIModel(
                model_id="qwen/qwen-3",
                name="Qwen 3",
                provider=ModelProvider.QWEN,
                version="3",
                release_date="2025-04-29",
                capabilities=["text", "code", "reasoning", "multilingual", "open_weights"],
                notes="Alibaba's open-weight model family.",
            ),
            AIModel(
                model_id="mistral/mistral-large-3",
                name="Mistral Large 3",
                provider=ModelProvider.MISTRAL,
                version="3",
                release_date="2025-07-15",
                capabilities=["text", "code", "reasoning", "multilingual"],
                notes="French AI company. EU AI Act compliant by design.",
            ),
            AIModel(
                model_id="anthropic/claude-fable-5",
                name="Claude Fable 5",
                provider=ModelProvider.ANTHROPIC,
                version="5",
                release_date="2026-06-01",
                capabilities=["text", "code", "reasoning", "creative_writing"],
                notes="RESTRICTED: US government ordered shutdown June 2026 (export control, national security).",
            ),
            AIModel(
                model_id="anthropic/claude-mythos-5",
                name="Claude Mythos 5",
                provider=ModelProvider.ANTHROPIC,
                version="5",
                release_date="2026-06-01",
                capabilities=["text", "code", "reasoning", "advanced_reasoning"],
                notes="RESTRICTED: US government ordered shutdown June 2026 (export control, national security).",
            ),
        ]

        for m in models:
            self._models[m.model_id] = m

        # Seed regulatory statuses based on real June 2026 events
        statuses = [
            # US restrictions on Anthropic Fable 5 / Mythos 5
            RegulatoryStatus(
                model_id="anthropic/claude-fable-5",
                jurisdiction=Jurisdiction.US,
                risk_level=RiskLevel.BANNED,
                use_case=UseCase.GENERAL,
                restrictions=[
                    "US government ordered global shutdown June 2026",
                    "Export control / national security grounds",
                    "Anthropic must not distribute this model",
                ],
                source_url="https://techcrunch.com/2026/06/13/anthropics-safety-warnings-may-have-just-backfired/",
                notes="Government pulled the plug after Amazon CEO raised concerns with Treasury.",
            ),
            RegulatoryStatus(
                model_id="anthropic/claude-fable-5",
                jurisdiction=Jurisdiction.US,
                risk_level=RiskLevel.BANNED,
                use_case=UseCase.DEFENSE,
                restrictions=[
                    "Banned for defense use by US government order",
                ],
                source_url="https://techcrunch.com/2026/06/13/anthropics-safety-warnings-may-have-just-backfired/",
            ),
            RegulatoryStatus(
                model_id="anthropic/claude-mythos-5",
                jurisdiction=Jurisdiction.US,
                risk_level=RiskLevel.BANNED,
                use_case=UseCase.GENERAL,
                restrictions=[
                    "US government ordered global shutdown June 2026",
                    "Export control / national security grounds",
                ],
                source_url="https://techcrunch.com/2026/06/13/anthropics-safety-warnings-may-have-just-backfired/",
            ),
            # OpenAI under state AG investigation
            RegulatoryStatus(
                model_id="openai/gpt-4o",
                jurisdiction=Jurisdiction.US,
                risk_level=RiskLevel.PENDING_REVIEW,
                use_case=UseCase.GENERAL,
                restrictions=[
                    "OpenAI faces state attorney general investigation",
                    "Monitor for compliance requirements",
                ],
                source_url="https://techcrunch.com/2026/06/13/openai-faces-investigation-from-state-attorneys-general/",
            ),
            RegulatoryStatus(
                model_id="openai/gpt-5",
                jurisdiction=Jurisdiction.US,
                risk_level=RiskLevel.PENDING_REVIEW,
                use_case=UseCase.GENERAL,
                restrictions=[
                    "OpenAI faces state attorney general investigation",
                    "Monitor for compliance requirements",
                ],
                source_url="https://techcrunch.com/2026/06/13/openai-faces-investigation-from-state-attorneys-general/",
            ),
            # India — lost access to frontier models
            RegulatoryStatus(
                model_id="anthropic/claude-fable-5",
                jurisdiction=Jurisdiction.IN,
                risk_level=RiskLevel.BANNED,
                use_case=UseCase.GENERAL,
                restrictions=[
                    "India lost access after US government shutdown",
                    "India debating domestic AI capabilities",
                ],
                source_url="https://techcrunch.com/2026/06/13/as-anthropic-suspends-access-to-new-models-india-debates-its-ai-future/",
            ),
            RegulatoryStatus(
                model_id="anthropic/claude-mythos-5",
                jurisdiction=Jurisdiction.IN,
                risk_level=RiskLevel.BANNED,
                use_case=UseCase.GENERAL,
                restrictions=[
                    "India lost access after US government shutdown",
                ],
                source_url="https://techcrunch.com/2026/06/13/as-anthropic-suspends-access-to-new-models-india-debates-its-ai-future/",
            ),
            # Chinese models — export control considerations
            RegulatoryStatus(
                model_id="deepseek/deepseek-v3",
                jurisdiction=Jurisdiction.US,
                risk_level=RiskLevel.RESTRICTED,
                use_case=UseCase.GOVERNMENT,
                restrictions=[
                    "Chinese model — restricted for US government use",
                    "Export control screening required",
                    "Data residency: data processed in China",
                ],
                notes="Open weights but Chinese origin. Screen for government/defense use.",
            ),
            RegulatoryStatus(
                model_id="deepseek/deepseek-r1",
                jurisdiction=Jurisdiction.US,
                risk_level=RiskLevel.RESTRICTED,
                use_case=UseCase.GOVERNMENT,
                restrictions=[
                    "Chinese model — restricted for US government use",
                    "Export control screening required",
                ],
            ),
            RegulatoryStatus(
                model_id="zai/glm-5.2",
                jurisdiction=Jurisdiction.US,
                risk_level=RiskLevel.RESTRICTED,
                use_case=UseCase.GOVERNMENT,
                restrictions=[
                    "Chinese model — restricted for US government use",
                    "Export control screening required",
                ],
            ),
            RegulatoryStatus(
                model_id="deepseek/deepseek-v3",
                jurisdiction=Jurisdiction.US,
                risk_level=RiskLevel.COMPLIANT,
                use_case=UseCase.GENERAL,
                restrictions=["Data residency: data processed in China"],
                notes="Open weights. Commercial use generally allowed but monitor export control updates.",
            ),
            RegulatoryStatus(
                model_id="deepseek/deepseek-r1",
                jurisdiction=Jurisdiction.US,
                risk_level=RiskLevel.COMPLIANT,
                use_case=UseCase.GENERAL,
                restrictions=["Data residency: data processed in China"],
            ),
            RegulatoryStatus(
                model_id="zai/glm-5.2",
                jurisdiction=Jurisdiction.US,
                risk_level=RiskLevel.COMPLIANT,
                use_case=UseCase.GENERAL,
                restrictions=["Data residency: data processed in China"],
            ),
            # EU — EU AI Act compliance
            RegulatoryStatus(
                model_id="openai/gpt-4o",
                jurisdiction=Jurisdiction.EU,
                risk_level=RiskLevel.COMPLIANT,
                use_case=UseCase.GENERAL,
                restrictions=["EU AI Act transparency requirements apply"],
                notes="Must disclose AI-generated content per EU AI Act.",
            ),
            RegulatoryStatus(
                model_id="openai/gpt-5",
                jurisdiction=Jurisdiction.EU,
                risk_level=RiskLevel.PENDING_REVIEW,
                use_case=UseCase.GENERAL,
                restrictions=[
                    "EU AI Act classification pending",
                    "May be classified as high-risk AI system",
                ],
            ),
            RegulatoryStatus(
                model_id="anthropic/claude-sonnet-4",
                jurisdiction=Jurisdiction.EU,
                risk_level=RiskLevel.COMPLIANT,
                use_case=UseCase.GENERAL,
                restrictions=["EU AI Act transparency requirements apply"],
            ),
            RegulatoryStatus(
                model_id="mistral/mistral-large-3",
                jurisdiction=Jurisdiction.EU,
                risk_level=RiskLevel.COMPLIANT,
                use_case=UseCase.GENERAL,
                restrictions=[],
                notes="French company. Designed for EU AI Act compliance.",
            ),
            # China — domestic models are compliant
            RegulatoryStatus(
                model_id="deepseek/deepseek-v3",
                jurisdiction=Jurisdiction.CN,
                risk_level=RiskLevel.COMPLIANT,
                use_case=UseCase.GENERAL,
                restrictions=[],
                notes="Chinese domestic model. Fully compliant in China.",
            ),
            RegulatoryStatus(
                model_id="zai/glm-5.2",
                jurisdiction=Jurisdiction.CN,
                risk_level=RiskLevel.COMPLIANT,
                use_case=UseCase.GENERAL,
                restrictions=[],
                notes="Chinese domestic model. Fully compliant in China.",
            ),
            RegulatoryStatus(
                model_id="qwen/qwen-3",
                jurisdiction=Jurisdiction.CN,
                risk_level=RiskLevel.COMPLIANT,
                use_case=UseCase.GENERAL,
                restrictions=[],
                notes="Alibaba model. Fully compliant in China.",
            ),
            # Meta — Llama 4 (open weights, but Manus deal fallout)
            RegulatoryStatus(
                model_id="meta/llama-4-maverick",
                jurisdiction=Jurisdiction.US,
                risk_level=RiskLevel.COMPLIANT,
                use_case=UseCase.GENERAL,
                restrictions=[],
                notes="Open weights. Meta unwound $2B Manus deal after Beijing demands — monitor for future restrictions.",
            ),
            # Google — generally compliant
            RegulatoryStatus(
                model_id="google/gemini-2.5-pro",
                jurisdiction=Jurisdiction.US,
                risk_level=RiskLevel.COMPLIANT,
                use_case=UseCase.GENERAL,
                restrictions=[],
            ),
            RegulatoryStatus(
                model_id="google/gemini-2.5-flash",
                jurisdiction=Jurisdiction.US,
                risk_level=RiskLevel.COMPLIANT,
                use_case=UseCase.GENERAL,
                restrictions=[],
            ),
        ]

        for s in statuses:
            self._statuses.append(s)

        # Seed alerts for the most critical changes
        alerts = [
            Alert(
                alert_id="ALT-001",
                model_id="anthropic/claude-fable-5",
                model_name="Claude Fable 5",
                jurisdiction=Jurisdiction.US,
                previous_status=RiskLevel.COMPLIANT,
                new_status=RiskLevel.BANNED,
                description="US government ordered global shutdown of Claude Fable 5 (export control, national security). Anthropic must not distribute.",
                created_at=datetime(2026, 6, 13, 14, 0, tzinfo=timezone.utc),
            ),
            Alert(
                alert_id="ALT-002",
                model_id="anthropic/claude-mythos-5",
                model_name="Claude Mythos 5",
                jurisdiction=Jurisdiction.US,
                previous_status=RiskLevel.COMPLIANT,
                new_status=RiskLevel.BANNED,
                description="US government ordered global shutdown of Claude Mythos 5 (export control, national security).",
                created_at=datetime(2026, 6, 13, 14, 0, tzinfo=timezone.utc),
            ),
            Alert(
                alert_id="ALT-003",
                model_id="openai/gpt-4o",
                model_name="GPT-4o",
                jurisdiction=Jurisdiction.US,
                previous_status=RiskLevel.COMPLIANT,
                new_status=RiskLevel.PENDING_REVIEW,
                description="OpenAI faces investigation from state attorneys general. Monitor for compliance requirements.",
                created_at=datetime(2026, 6, 13, 10, 0, tzinfo=timezone.utc),
            ),
            Alert(
                alert_id="ALT-004",
                model_id="anthropic/claude-fable-5",
                model_name="Claude Fable 5",
                jurisdiction=Jurisdiction.IN,
                previous_status=RiskLevel.COMPLIANT,
                new_status=RiskLevel.BANNED,
                description="India lost access to Claude Fable 5 after US government shutdown. India debating domestic AI capabilities.",
                created_at=datetime(2026, 6, 13, 16, 0, tzinfo=timezone.utc),
            ),
        ]

        for a in alerts:
            self._alerts.append(a)


# Singleton store instance
store = RegShieldStore()
