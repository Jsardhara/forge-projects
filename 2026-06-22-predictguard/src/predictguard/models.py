"""Data models for PredictGuard."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Jurisdiction(str, Enum):
    """US states and international jurisdictions with prediction market regulation."""
    # US States
    ALABAMA = "AL"
    ALASKA = "AK"
    ARIZONA = "AZ"
    ARKANSAS = "AR"
    CALIFORNIA = "CA"
    COLORADO = "CO"
    CONNECTICUT = "CT"
    DELAWARE = "DE"
    FLORIDA = "FL"
    GEORGIA = "GA"
    HAWAII = "HI"
    IDAHO = "ID"
    ILLINOIS = "IL"
    INDIANA = "IN"
    IOWA = "IA"
    KANSAS = "KS"
    KENTUCKY = "KY"
    LOUISIANA = "LA"
    MAINE = "ME"
    MARYLAND = "MD"
    MASSACHUSETTS = "MA"
    MICHIGAN = "MI"
    MINNESOTA = "MN"
    MISSISSIPPI = "MS"
    MISSOURI = "MO"
    MONTANA = "MT"
    NEBRASKA = "NE"
    NEVADA = "NV"
    NEW_HAMPSHIRE = "NH"
    NEW_JERSEY = "NJ"
    NEW_MEXICO = "NM"
    NEW_YORK = "NY"
    NORTH_CAROLINA = "NC"
    NORTH_DAKOTA = "ND"
    OHIO = "OH"
    OKLAHOMA = "OK"
    OREGON = "OR"
    PENNSYLVANIA = "PA"
    RHODE_ISLAND = "RI"
    SOUTH_CAROLINA = "SC"
    SOUTH_DAKOTA = "SD"
    TENNESSEE = "TN"
    TEXAS = "TX"
    UTAH = "UT"
    VERMONT = "VT"
    VIRGINIA = "VA"
    WASHINGTON = "WA"
    WEST_VIRGINIA = "WV"
    WISCONSIN = "WI"
    WYOMING = "WY"
    DISTRICT_OF_COLUMBIA = "DC"
    # International
    UNITED_KINGDOM = "UK"
    EUROPEAN_UNION = "EU"
    CANADA = "CA-INT"
    AUSTRALIA = "AU"
    JAPAN = "JP"
    SINGAPORE = "SG"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class RegulatoryStatus:
    """Regulatory status for a specific jurisdiction."""
    jurisdiction: Jurisdiction
    status: str  # "ALLOWED", "RESTRICTED", "CEASE_AND_DESIST", "BAN_PROPOSED", "UNCLEAR"
    notes: str = ""
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cftc_compliant: bool = False
    state_license_required: bool = False
    kyc_required: bool = False
    restrictions: list[str] = field(default_factory=list)


@dataclass
class Market:
    """A prediction market."""
    mid: str
    question: str
    category: str  # politics, sports, economics, crypto, culture, other
    outcome_prices: dict[str, float] = field(default_factory=dict)
    volume_24h: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    outcome: Optional[str] = None


@dataclass
class Trade:
    """A single trade in a prediction market."""
    tid: str
    market_id: str
    trader_id: str
    side: str  # "buy" or "sell"
    outcome: str  # e.g., "Yes", "No", "Trump", "Harris"
    price: float  # 0.0 to 1.0 (cents on the dollar)
    quantity: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    platform: str = ""  # "kalshi", "polymarket", "crypto_com", etc.
    jurisdiction: Optional[Jurisdiction] = None


@dataclass
class RiskAssessment:
    """Risk assessment for a trader or market."""
    target_id: str  # trader_id or market_id
    target_type: str  # "trader" or "market"
    risk_level: RiskLevel
    risk_score: float  # 0.0 to 1.0
    flags: list[str] = field(default_factory=list)
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict = field(default_factory=dict)


@dataclass
class AuditEntry:
    """A single audit trail entry."""
    eid: str
    event_type: str  # "trade", "report_generated", "risk_alert", "compliance_check"
    actor: str
    description: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)
    data_hash: str = ""  # SHA-256 hash of the entry data for integrity


@dataclass
class ComplianceReport:
    """A compliance report for a given period and jurisdiction."""
    rid: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    jurisdiction: Optional[Jurisdiction] = None
    total_trades: int = 0
    total_volume: float = 0.0
    flagged_trades: int = 0
    risk_assessments: list[RiskAssessment] = field(default_factory=list)
    compliance_score: float = 1.0  # 0.0 to 1.0 (1.0 = fully compliant)
    findings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
