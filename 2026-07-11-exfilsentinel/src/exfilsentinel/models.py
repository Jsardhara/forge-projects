from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class RiskClass(str, Enum):
    BENIGN = "benign"
    SUSPICIOUS = "suspicious"
    EXFILTRATION = "exfiltration"


@dataclass(frozen=True)
class ApiEvent:
    """A single model-API access event."""

    actor_id: str
    model: str
    timestamp: datetime
    prompt_tokens: int = 0
    completion_tokens: int = 0
    endpoint: str = "/v1/chat/completions"
    ip: str = ""
    prompt_template_hash: str = ""

    def __post_init__(self) -> None:
        # Normalize to timezone-aware UTC so comparisons never mix naive/aware.
        if self.timestamp.tzinfo is None:
            object.__setattr__(self, "timestamp", self.timestamp.replace(tzinfo=timezone.utc))


@dataclass(frozen=True)
class ExtractionSignal:
    name: str
    weight: float
    raw_score: float
    detail: str = ""


@dataclass(frozen=True)
class ExtractionVerdict:
    actor_id: str
    risk_score: float
    risk_class: RiskClass
    signals: tuple[ExtractionSignal, ...] = field(default_factory=tuple)
    evidence: tuple[str, ...] = field(default_factory=tuple)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def triggered(self) -> tuple[ExtractionSignal, ...]:
        return tuple(s for s in self.signals if s.raw_score > 0.0)


@dataclass(frozen=True)
class ProvenanceRecord:
    org_id: str
    model: str
    issued_at: datetime
    nonce: str


@dataclass(frozen=True)
class Watermark:
    record: ProvenanceRecord
    payload_bits: str
    text: str
