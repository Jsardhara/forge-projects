"""Pydantic models for RegShield data structures."""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class RiskLevel(str, enum.Enum):
    """Compliance risk level for a model in a jurisdiction."""
    COMPLIANT = "compliant"
    RESTRICTED = "restricted"
    PENDING_REVIEW = "pending_review"
    BANNED = "banned"
    UNKNOWN = "unknown"


class ModelProvider(str, enum.Enum):
    """Known AI model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    META = "meta"
    MISTRAL = "mistral"
    DEEPSEEK = "deepseek"
    ZAI = "zai"  # GLM
    MOONSHOT = "moonshot"
    BAICHUAN = "baichuan"
    QWEN = "qwen"
    OTHER = "other"


class UseCase(str, enum.Enum):
    """Common AI use cases with different regulatory treatment."""
    GENERAL = "general"
    HEALTHCARE = "healthcare"
    FINANCIAL = "financial"
    GOVERNMENT = "government"
    DEFENSE = "defense"
    EDUCATION = "education"
    RESEARCH = "research"
    EXPORT = "export"


class Jurisdiction(str, enum.Enum):
    """Supported jurisdictions."""
    US = "US"
    EU = "EU"
    UK = "UK"
    CN = "CN"
    IN = "IN"
    CA = "CA"
    AU = "AU"
    JP = "JP"
    KR = "KR"
    BR = "BR"


class AIModel(BaseModel):
    """Represents an AI model tracked by RegShield."""
    model_id: str = Field(..., description="Unique model identifier")
    name: str = Field(..., description="Human-readable model name")
    provider: ModelProvider
    version: str = Field(default="latest")
    release_date: Optional[str] = None
    capabilities: list[str] = Field(default_factory=list)
    notes: str = ""


class RegulatoryStatus(BaseModel):
    """Regulatory status of a model in a specific jurisdiction."""
    model_id: str
    jurisdiction: Jurisdiction
    risk_level: RiskLevel
    use_case: UseCase = UseCase.GENERAL
    restrictions: list[str] = Field(default_factory=list)
    source_url: str = ""
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    notes: str = ""


class ComplianceCheckRequest(BaseModel):
    """Request to check compliance for a model in a jurisdiction."""
    model_id: str
    jurisdiction: Jurisdiction
    use_case: UseCase = UseCase.GENERAL


class ComplianceCheckResult(BaseModel):
    """Result of a compliance check."""
    model_id: str
    model_name: str
    jurisdiction: Jurisdiction
    use_case: UseCase
    risk_level: RiskLevel
    is_allowed: bool
    restrictions: list[str] = Field(default_factory=list)
    source_url: str = ""
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    notes: str = ""


class Alert(BaseModel):
    """A regulatory change alert."""
    alert_id: str
    model_id: str
    model_name: str
    jurisdiction: Jurisdiction
    previous_status: RiskLevel
    new_status: RiskLevel
    description: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    acknowledged: bool = False


class AuditEntry(BaseModel):
    """An audit log entry for compliance checks."""
    entry_id: str
    action: str
    model_id: str
    jurisdiction: Jurisdiction
    use_case: UseCase
    result: RiskLevel
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    details: str = ""
