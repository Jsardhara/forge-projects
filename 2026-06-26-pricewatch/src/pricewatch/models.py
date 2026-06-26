"""Data models for PriceWatch — provider-agnostic pricing structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Provider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"


class Tier(Enum):
    FLAGSHIP = "flagship"    # GPT-4o, Claude Opus, Gemini Ultra
    MID = "mid"              # GPT-4o-mini, Claude Sonnet, Gemini Pro
    FAST = "fast"            # GPT-3.5, Claude Haiku, Gemini Flash
    REASONING = "reasoning"  # o1, o3, Claude Opus (extended thinking)
    EMBEDDING = "embedding"  # text-embedding-3, voyage, etc.


class ChangeDirection(Enum):
    PRICE_DROP = "price_drop"
    PRICE_INCREASE = "price_increase"
    NEW_MODEL = "new_model"
    NO_CHANGE = "no_change"


class AlertSeverity(Enum):
    CRITICAL = "critical"    # >50% change or price war
    HIGH = "high"           # 25-50% change
    MEDIUM = "medium"       # 10-25% change
    LOW = "low"             # <10% change
    INFO = "info"           # new model listing


@dataclass(frozen=True)
class ModelPricing:
    """Pricing data for a single model from a single provider."""
    provider: Provider
    model_id: str
    tier: Tier
    input_price_per_mtok: float   # USD per 1M input tokens
    output_price_per_mtok: float  # USD per 1M output tokens
    context_window: int           # max context tokens
    snapshot_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def blended_price(self) -> float:
        """Blended price assuming 50/50 input/output split."""
        return (self.input_price_per_mtok + self.output_price_per_mtok) / 2

    @property
    def price_per_1k_context(self) -> float:
        """Cost efficiency: blended price normalized by context window."""
        if self.context_window <= 0:
            return self.blended_price
        return self.blended_price / (self.context_window / 1000)


@dataclass(frozen=True)
class PriceDelta:
    """Detected change in model pricing between two snapshots."""
    provider: Provider
    model_id: str
    direction: ChangeDirection
    input_delta: float     # absolute change in input price
    output_delta: float    # absolute change in output price
    input_pct: float       # percentage change in input price
    output_pct: float      # percentage change in output price
    old_input: float
    old_output: float
    new_input: float
    new_output: float
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def max_pct(self) -> float:
        """Maximum percentage change (absolute value) across input and output."""
        return max(abs(self.input_pct), abs(self.output_pct))


@dataclass(frozen=True)
class PriceAlert:
    """Structured alert generated from a price change."""
    provider: Provider
    model_id: str
    severity: AlertSeverity
    direction: ChangeDirection
    message: str
    detail: str
    max_pct: float
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ModelRanking:
    """A model ranked by cost-efficiency within its tier."""
    rank: int
    pricing: ModelPricing
    score: float  # lower is better (blended price)
    tier: Tier


@dataclass
class PriceSnapshot:
    """A complete snapshot of all model prices at a point in time."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    entries: list[ModelPricing] = field(default_factory=list)

    def by_provider(self, provider: Provider) -> list[ModelPricing]:
        return [e for e in self.entries if e.provider == provider]

    def by_tier(self, tier: Tier) -> list[ModelPricing]:
        return [e for e in self.entries if e.tier == tier]

    def by_model(self, model_id: str) -> list[ModelPricing]:
        return [e for e in self.entries if e.model_id == model_id]
