"""Core models for capalarm: plans, usage samples, and assessments."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Plan:
    """A capped AI subscription plan: token cap + optional rate-limit tier.

    Coordinates are timezone-aware UTC. Attributes:
      id         -- stable plan id (e.g. 'anthropic-claude-max')
      provider   -- provider slug (e.g. 'anthropic')
      name       -- human-readable plan name
      hard_cap   -- monthly token hard cap (the enforcement ceiling)
      soft_cap   -- monthly token soft cap; crossing it triggers throughput
                    degradation (usually a fraction of hard_cap). If None,
                    derived as soft_cap_ratio * hard_cap.
      soft_cap_ratio -- ratio (0..1) used to derive soft_cap when not given.
      rate_limit -- max tokens-per-minute allowed (None if not rate-tiered).
      period_days -- subscription period used for remaining-days math.
    """

    id: str
    provider: str
    name: str
    hard_cap: int
    soft_cap: Optional[int] = None
    soft_cap_ratio: float = 0.8
    rate_limit: Optional[int] = None
    period_days: int = 30

    def effective_soft_cap(self) -> int:
        if self.soft_cap is not None:
            return self.soft_cap
        return int(self.hard_cap * self.soft_cap_ratio)


@dataclass(frozen=True)
class UsageSample:
    """A single usage record: provider + timestamp + tokens consumed."""

    provider: str
    timestamp: datetime
    tokens: int


@dataclass
class PlanUsage:
    """Aggregated usage for one provider across the observed window."""

    provider: str
    plans: list[Plan] = field(default_factory=list)
    total_tokens: int = 0
    # provider-first seen vs last seen (timezone-aware)
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    peak_tokens_per_min: int = 0


@dataclass
class BreachForecast:
    """Projected days-until-hard-cap-breach for a provider under linear burn."""

    provider: str
    days_to_cap: Optional[float] = None  # None => won't breach within horizon
    daily_burn: float = 0.0
    remaining_tokens: int = 0


@dataclass
class Severity:
    """Enumerated severity levels. Ordering: PASS < WARN < CRIT."""

    PASS = "PASS"
    WARN = "WARN"
    CRIT = "CRIT"

    _order = {PASS: 0, WARN: 1, CRIT: 2}

    @classmethod
    def worst(cls, *levels: str) -> str:
        """Return the most severe level among the given set."""
        best = cls.PASS
        for lvl in levels:
            if cls._order.get(lvl, 0) > cls._order.get(best, 0):
                best = lvl
        return best


@dataclass
class Finding:
    """One evaluated check result for a provider."""

    rule: str
    severity: str
    message: str