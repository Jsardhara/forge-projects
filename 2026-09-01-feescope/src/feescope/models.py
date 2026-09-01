"""feescope -- core domain models and shared severity vocabulary.

This module is the LOWEST layer: it owns the `Severity` / `Verdict` enums and the
integer `SEVERITY_RANK` map that every other module imports. Do not re-define
severity ordering in engine.py / cli.py -- pull it from here (single source of truth).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional


class Severity(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FLAG = "FLAG"


class Verdict(Enum):
    CLEAR = "CLEAR"
    WARN = "WARN"
    FLAG = "FLAG"


# Integer severity rank for max()/min() comparisons. NEVER compare on
# Severity.value (string) -- 'PASS'(P=80) sorts ABOVE 'FLAG'(F=70) lexicographically.
SEVERITY_RANK = {Severity.PASS: 0, Severity.WARN: 1, Severity.FLAG: 2}
VERDICT_FROM_RANK = {0: Verdict.CLEAR, 1: Verdict.WARN, 2: Verdict.FLAG}

# Magnitude weight per finding (score = capped sum of these). Verdict stays
# severity-DOMINANT (worst single finding), score is only the weighted magnitude.
SEVERITY_SCORE = {Severity.PASS: 0, Severity.WARN: 25, Severity.FLAG: 55}


@dataclass
class FeeItem:
    """A single billing line item on an ad-media invoice.

    category: 'media' | 'fee' | 'discount' | 'tax' | 'other'.
    verified: confirmed spend from a trusted independent source (optional).
    attached_to: base purchase id this fee line hangs off (for stacking checks).
    """

    line_id: str
    description: str = ""
    amount: float = 0.0
    category: str = "media"
    verified: Optional[float] = None
    attached_to: Optional[str] = None


@dataclass
class Finding:
    code: str  # FEE-001 .. FEE-005
    severity: Severity
    detail: str
    line_id: Optional[str] = None


@dataclass
class InvoiceReport:
    invoice_id: str
    verdict: Verdict
    score: float  # 0-100 magnitude; verdict is severity-dominant, not this
    findings: List[Finding] = field(default_factory=list)
    total_billed: float = 0.0
    total_fees: float = 0.0
    fee_ratio: float = 0.0
    scanned_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    @property
    def message(self) -> str:
        return f"{self.verdict.value} {int(round(self.score))}/100"