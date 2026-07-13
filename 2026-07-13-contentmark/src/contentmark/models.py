"""Data models for contentmark — frozen, transparent, dependency-free."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


def clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


class SignalId(str, Enum):
    BURSTINESS = "burstiness"
    REPETITION = "repetition"
    CONNECTOR_FREQUENCY = "connector_frequency"
    LOW_PERPLEXITY_WORDS = "low_perplexity_words"
    FILLER_DENSITY = "filler_density"
    ENUMERATION_DENSITY = "enumeration_density"
    SENTENCE_UNIFORMITY = "sentence_uniformity"


class LikelihoodBand(str, Enum):
    HUMAN = "human"
    POSSIBLY_AI = "possibly_ai"
    LIKELY_AI = "likely_ai"
    VERY_LIKELY_AI = "very_likely_ai"


# Deterministic band thresholds on the normalized [0,1] score.
BAND_THRESHOLDS = (
    (0.62, LikelihoodBand.VERY_LIKELY_AI),
    (0.45, LikelihoodBand.LIKELY_AI),
    (0.28, LikelihoodBand.POSSIBLY_AI),
)


def band_for_score(score: float) -> LikelihoodBand:
    s = clamp01(score)
    for threshold, band in BAND_THRESHOLDS:
        if s >= threshold:
            return band
    return LikelihoodBand.HUMAN


@dataclass(frozen=True)
class SignalResult:
    signal_id: SignalId
    weight: float
    raw_score: float          # 0..1 unweighted signal strength
    contribution: float       # weight * raw_score
    detail: str

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id.value,
            "weight": round(self.weight, 3),
            "raw_score": round(self.raw_score, 4),
            "contribution": round(self.contribution, 4),
            "detail": self.detail,
        }


@dataclass(frozen=True)
class DetectionReport:
    char_count: int
    word_count: int
    sentence_count: int
    scores: list
    overall_raw: float                 # sum of contributions, pre-normalization
    normalized_score: float            # 0..1
    band: LikelihoodBand
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    label: Optional[str] = None        # optional provenance label if text was labeled

    def to_dict(self) -> dict:
        return {
            "char_count": self.char_count,
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "signals": [s.to_dict() for s in self.scores],
            "overall_raw": round(self.overall_raw, 4),
            "normalized_score": round(self.normalized_score, 4),
            "band": self.band.value,
            "generated_at": self.generated_at.isoformat(),
            "label": self.label,
        }

    def explain(self) -> str:
        lines = [
            f"AI-content signal: {self.band.value} (score {self.normalized_score:.3f})",
            f"  text: {self.word_count} words / {self.sentence_count} sentences",
        ]
        for s in sorted(self.scores, key=lambda x: -x.contribution):
            lines.append(
                f"  - {s.signal_id.value}: +{s.contribution:.3f} "
                f"(raw {s.raw_score:.3f} x w {s.weight:.2f}) — {s.detail}"
            )
        return "\n".join(lines)


class ProvenanceLabel(str, Enum):
    HUMAN = "human"
    AI_ASSISTED = "ai_assisted"
    AI_GENERATED = "ai_generated"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Provenance:
    rid: str
    label: ProvenanceLabel
    tool: Optional[str] = None
    model: Optional[str] = None
    author: Optional[str] = None
    note: Optional[str] = None
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "rid": self.rid,
            "label": self.label.value,
            "tool": self.tool,
            "model": self.model,
            "author": self.author,
            "note": self.note,
            "generated_at": self.generated_at.isoformat(),
        }

    @staticmethod
    def from_dict(d: dict) -> "Provenance":
        return Provenance(
            rid=d["rid"],
            label=ProvenanceLabel(d["label"]),
            tool=d.get("tool"),
            model=d.get("model"),
            author=d.get("author"),
            note=d.get("note"),
            generated_at=datetime.fromisoformat(d["generated_at"]),
        )


@dataclass(frozen=True)
class SignatureVerification:
    present: bool
    valid: bool
    tampered: bool
    rid: Optional[str] = None
    label: Optional[str] = None
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "present": self.present,
            "valid": self.valid,
            "tampered": self.tampered,
            "rid": self.rid,
            "label": self.label,
            "detail": self.detail,
        }
