"""Data models for restrictbot."""

from dataclasses import dataclass, field
from enum import Enum


class RestrictionLevel(str, Enum):
    BANNED = "banned"
    RESTRICTED = "restricted"
    MONITORED = "monitored"


class Verdict(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass(frozen=True)
class RestrictedCategory:
    """A single restricted category under the US foreign-made ban."""
    slug: str
    name: str
    level: RestrictionLevel
    keywords: tuple[str, ...]  # keywords to match in product descriptions
    description: str
    source: str = "USG 2026-07-29 ban"


@dataclass(frozen=True)
class Finding:
    category: str
    verdict: Verdict
    reason: str
    match: str  # what matched


@dataclass
class ScanResult:
    product_name: str
    description: str
    verdict: Verdict
    findings: list[Finding] = field(default_factory=list)
    score: float = 0.0  # 0.0 (safe) - 1.0 (highly restricted)

    def to_dict(self) -> dict:
        return {
            "product_name": self.product_name,
            "verdict": self.verdict.value,
            "findings": [{
                "category": f.category,
                "verdict": f.verdict.value,
                "reason": f.reason,
                "match": f.match,
            } for f in self.findings],
            "score": round(self.score, 2),
        }