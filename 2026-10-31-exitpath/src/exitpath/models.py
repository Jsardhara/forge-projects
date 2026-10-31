"""Exit-path vocabulary: one state ladder, one immutable record per measurement.

The ladder is integer-ranked on purpose. `max(..., key=lambda s: s)` over the state
*strings* would compare "operational" > "halted" lexicographically and quietly report a
halted venue as fine -- the same trap that broke songguard's verdict aggregation.
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple

OPEN = "open"
DEGRADED = "degraded"
HALTED = "halted"
UNMEASURABLE = "unmeasurable"

STATE_RANK = {OPEN: 0, DEGRADED: 1, HALTED: 2}

# statuspage.io component status -> exit state
COMPONENT_STATE = {
    "operational": OPEN,
    "under_maintenance": DEGRADED,
    "degraded_performance": DEGRADED,
    "partial_outage": HALTED,
    "major_outage": HALTED,
}


def worst(states):
    """Most severe state, ignoring UNMEASURABLE (it is not a severity)."""
    ranked = [s for s in states if s in STATE_RANK]
    if not ranked:
        return UNMEASURABLE
    return max(ranked, key=lambda s: STATE_RANK[s])


@dataclass(frozen=True)
class Fetch:
    """Transport result. A 404 is data, not an exception."""

    status: int
    body: bytes = b""
    error: Optional[str] = None


@dataclass(frozen=True)
class Signal:
    """One statuspage component that bears on exit, and the state it implies."""

    component: str
    state: str
    note: str = ""


@dataclass(frozen=True)
class VenueExit:
    slug: str
    name: str
    kind: str
    state: str
    signals: Tuple[Signal, ...] = field(default_factory=tuple)
    paused_networks: Tuple[str, ...] = field(default_factory=tuple)
    degraded_networks: Tuple[str, ...] = field(default_factory=tuple)
    source_url: str = ""
    http_code: int = 0
    confidence: float = 0.0
    reason: Optional[str] = None
    observed_at: Optional[str] = None
    checked: int = 0
    page_status: Optional[str] = None

    @property
    def measurable(self):
        return self.state != UNMEASURABLE


@dataclass(frozen=True)
class ChainHealth:
    chain: str
    endpoint: str
    ok: bool
    block_height: Optional[int] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None
