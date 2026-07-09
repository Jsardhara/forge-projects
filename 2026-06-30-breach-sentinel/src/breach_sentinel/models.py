"""Data models for BreachSentinel.

All records are frozen dataclasses — once a breach record or audit entry
is created it must never be mutated (integrity of the exposure history).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class BreachType(str, Enum):
    """Category of leaked data. Ordered roughly by sensitivity."""

    EMAIL = "email"
    PHONE = "phone"
    PASSWORD = "password"
    API_KEY = "api_key"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    PASSPORT = "passport"
    OTHER = "other"


class Severity(str, Enum):
    """Exposure severity, ordered low -> critical."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_rank(cls, rank: int) -> "Severity":
        ranks = [cls.INFO, cls.LOW, cls.MEDIUM, cls.HIGH, cls.CRITICAL]
        idx = max(0, min(len(ranks) - 1, rank))
        return ranks[idx]

    @property
    def rank(self) -> int:
        order = [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        return order.index(self)


# Sensitivity weight per breach type (higher = more dangerous leak).
SENSITIVITY_WEIGHT: dict[BreachType, int] = {
    BreachType.EMAIL: 2,
    BreachType.PHONE: 3,
    BreachType.PASSWORD: 4,
    BreachType.API_KEY: 5,
    BreachType.CREDIT_CARD: 6,
    BreachType.SSN: 8,
    BreachType.PASSPORT: 8,
    BreachType.OTHER: 2,
}


@dataclass(frozen=True)
class Identity:
    """A watched identity (person or account) to monitor for exposure.

    Only one identifying value needs to be set. ``label`` is a human
    friendly name; ``iid`` is the stable primary key.
    """

    iid: str
    label: str
    email: Optional[str] = None
    phone: Optional[str] = None
    passport: Optional[str] = None
    ssn: Optional[str] = None
    note: Optional[str] = None

    def search_keys(self) -> list[str]:
        """Return the non-empty identifying values to scan with sources."""
        keys: list[str] = []
        for val in (self.email, self.phone, self.passport, self.ssn):
            if val:
                keys.append(val)
        return keys


@dataclass(frozen=True)
class BreachSourceInfo:
    """Metadata describing a breach source / data set."""

    sid: str
    name: str
    source_type: str  # "api" | "local" | "paste"
    description: str = ""


@dataclass(frozen=True)
class BreachRecord:
    """A single observation that an identity value appeared in a breach.

    ``bid`` is deterministic (hash of source+identity+breach+datatype) so
    re-scans are idempotent and dedupe cleanly.
    """

    bid: str
    source_id: str
    identity_value: str
    breach_type: BreachType
    breach_name: str
    breach_date: Optional[datetime] = None
    added_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""
    password_pwned_count: Optional[int] = None  # for Pwned Passwords range hits

    @staticmethod
    def make_bid(
        source_id: str, identity_value: str, breach_type: BreachType, breach_name: str
    ) -> str:
        raw = f"{source_id}|{identity_value.lower()}|{breach_type.value}|{breach_name}".encode(
            "utf-8"
        )
        return hashlib.sha256(raw).hexdigest()[:16]


@dataclass(frozen=True)
class ExposureScore:
    """Computed exposure assessment for one identity."""

    iid: str
    score: int  # 0-100
    severity: Severity
    record_count: int
    critical_types: list[BreachType]
    latest_breach: Optional[datetime] = None
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Alert:
    """An actionable alert produced when exposure crosses a threshold."""

    aid: str
    iid: str
    severity: Severity
    title: str
    body: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def make_aid(iid: str, title: str) -> str:
        raw = f"{iid}|{title}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]


@dataclass(frozen=True)
class ScanResult:
    """Result of scanning one identity against configured sources."""

    iid: str
    label: str
    records: tuple[BreachRecord, ...]
    score: ExposureScore
    alerts: tuple[Alert, ...]
    scanned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
