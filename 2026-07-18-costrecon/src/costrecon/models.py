"""Data models for costrecon -- AWS billing reconciliation & idle-resource detection."""

from dataclasses import dataclass, field
from datetime import datetime, timezone as tz
from typing import Optional


@dataclass(frozen=True)
class LineItem:
    """A single Cost & Usage Report line item (normalized)."""

    line_item_id: str
    account_id: str
    service: str           # product/ProductName or lineItem/ProductCode
    region: str
    usage_type: str
    description: str
    cost: float            # unblended cost (may be negative for credits/RIs)
    usage_quantity: float
    resource_id: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None

    @property
    def is_credit(self) -> bool:
        return self.cost < 0


@dataclass
class Estimate:
    """An estimated / budgeted cost for a reconciliation key (e.g. a service)."""

    key: str
    estimated_cost: float
    note: str = ""


@dataclass
class Variance:
    """Reconciliation result for one key: estimated vs actual."""

    key: str
    estimated: float
    actual: float
    delta: float
    pct: Optional[float]    # (actual-estimated)/estimated*100; None if estimated == 0
    classification: str     # WITHIN_TOLERANCE / OVER_ESTIMATE / UNDER_ESTIMATE / UNESTIMATED / NO_ACTUAL
    anomaly: bool


@dataclass
class ReconciliationReport:
    by_key: list
    total_estimated: float
    total_actual: float
    anomalies: list
    unestimated_services: list
    generated_at: datetime = field(default_factory=lambda: datetime.now(tz.utc))


@dataclass
class ResourceUtilization:
    """A single billable resource and its utilization / state signal."""

    resource_id: str
    rtype: str                       # ec2 | ebs | eip | snapshot | rds | other
    utilization_pct: Optional[float] # CPU/utilization; None when N/A
    monthly_cost: float
    region: str = ""
    state: str = ""                  # e.g. "in-use" | "unattached" | "associated" | "available"
    age_days: Optional[float] = None # for snapshots


@dataclass
class IdleFinding:
    resource_id: str
    rtype: str
    reason: str
    severity: str       # INFO | WARN | CRITICAL
    monthly_cost: float
    estimated_savings: float


@dataclass
class IdleReport:
    findings: list
    total_savings: float
    total_cost: float
    generated_at: datetime = field(default_factory=lambda: datetime.now(tz.utc))
