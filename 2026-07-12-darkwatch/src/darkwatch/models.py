"""Data models for darkwatch.

Frozen dataclasses + enums. UTC-aware timestamps. No external dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Regulation(str, Enum):
    """Regulations darkwatch can flag against."""

    NYC_SUBSCRIPTIONS = "NYC Local Law — Deceptive Subscription Practices"
    EU_DSA = "EU DSA Art. 25 — Addictive Design / Minor Protection"
    EU_UCPD = "EU UCPD — Unfair Commercial Practices"
    FTC_NEGATIVE_OPTION = "FTC Negative-Option / Dark-Pattern Rule"


class Severity(str, Enum):
    """Finding severity. Higher = worse exposure."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def weight(self) -> float:
        return {
            Severity.CRITICAL: 1.0,
            Severity.HIGH: 0.7,
            Severity.MEDIUM: 0.4,
            Severity.LOW: 0.2,
        }[self]


class ComplianceBand(str, Enum):
    """Aggregate exposure band for a scanned page."""

    NON_COMPLIANT = "NON_COMPLIANT"  # >= 1 critical OR >= 3 findings total (rebalanced)
    NEEDS_REVIEW = "NEEDS_REVIEW"
    COMPLIANT = "COMPLIANT"


SEVERITY_ORDER = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]


@dataclass(frozen=True)
class Finding:
    """A single dark-pattern detection result."""

    rule_id: str
    title: str
    description: str
    regulation: Regulation
    severity: Severity
    evidence: str  # short evidence snippet or selector
    url: Optional[str] = None
    line: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "description": self.description,
            "regulation": self.regulation.value,
            "severity": self.severity.value,
            "evidence": self.evidence,
            "url": self.url,
            "line": self.line,
        }


@dataclass(frozen=True)
class RegulationCheck:
    """Pass/fail status of one regulation's heuristic coverage."""

    regulation: Regulation
    status: str  # "pass" | "fail" | "warn"
    findings: int
    critical: int
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "regulation": self.regulation.value,
            "status": self.status,
            "findings": self.findings,
            "critical": self.critical,
            "note": self.note,
        }


@dataclass
class ScanResult:
    """Aggregate result for a scanned page/flow."""

    url: str
    findings: List[Finding] = field(default_factory=list)
    band: ComplianceBand = ComplianceBand.COMPLIANT
    scanned_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "band": self.band.value,
            "findings": [f.to_dict() for f in self.findings],
            "scanned_at": self.scanned_at.isoformat(),
            "summary": self.summary(),
        }

    def summary(self) -> dict:
        counts = {s.value: 0 for s in Severity}
        for f in self.findings:
            counts[f.severity.value] += 1
        return {
            "total": len(self.findings),
            "by_severity": counts,
            "regulations": sorted({f.regulation.value for f in self.findings}),
        }
