"""Data models for aidisclose.

All models are frozen dataclasses for immutability. Field names avoid the
builtin ``id`` (use ``mid``) to prevent the ``id()`` shadowing trap.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional, Tuple

# CANONICAL obligation severities and their compliance weights.
# Higher weight = larger contribution to the overall gap score when unmet.
SEVERITY_WEIGHT = {
    "critical": 10,
    "high": 6,
    "medium": 3,
    "low": 1,
}


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MandateStatus(str, Enum):
    IN_FORCE = "in_force"
    UPCOMING = "upcoming"
    PROPOSED = "proposed"


@dataclass(frozen=True)
class Obligation:
    code: str
    label: str
    description: str
    severity: Severity = Severity.MEDIUM

    @property
    def weight(self) -> int:
        return SEVERITY_WEIGHT[self.severity.value]


@dataclass(frozen=True)
class Mandate:
    mid: str
    jurisdiction: str
    title: str
    summary: str
    obligations: Tuple[Obligation, ...]
    status: MandateStatus = MandateStatus.IN_FORCE
    effective_date: Optional[date] = None
    scope_sectors: Optional[Tuple[str, ...]] = None  # None => all sectors
    scope_uses: Optional[Tuple[str, ...]] = None      # None => any AI use
    penalty: str = ""
    source: str = ""

    def sector_applies(self, sectors: set) -> bool:
        if not self.scope_sectors:
            return True
        return bool(set(self.scope_sectors) & sectors)

    def use_applies(self, ai_uses: set) -> bool:
        if not self.scope_uses:
            return True
        return bool(set(self.scope_uses) & ai_uses)


@dataclass(frozen=True)
class OrgProfile:
    name: str
    sectors: Tuple[str, ...] = ()
    jurisdictions: Tuple[str, ...] = ()
    ai_uses: Tuple[str, ...] = ()
    implemented: Tuple[str, ...] = ()  # obligation codes already satisfied
    reference_date: Optional[date] = None

    def sectors_set(self) -> set:
        return set(self.sectors)

    def jurisdictions_set(self) -> set:
        return set(self.jurisdictions)

    def uses_set(self) -> set:
        return set(self.ai_uses)

    def implemented_set(self) -> set:
        return set(self.implemented)
