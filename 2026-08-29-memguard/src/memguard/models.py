"""memguard.models -- data structures for the memory-poisoning scanner."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(Enum):
    """Severity of a finding."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def weight(self) -> int:
        return {"LOW": 1, "MEDIUM": 3, "HIGH": 5, "CRITICAL": 10}[self.value]


class Verdict(Enum):
    """Overall scan verdict band."""
    CLEAN = "CLEAN"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class Finding:
    """A single detected signal."""
    rule_id: str
    category: str
    severity: Severity
    message: str
    matched_text: str
    file: str
    line: int
    column: int = 0

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "severity": self.severity.value,
            "message": self.message,
            "matched_text": self.matched_text,
            "file": self.file,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class ScanResult:
    """Aggregate result for one scanned path."""
    path: str
    findings: list = field(default_factory=list)
    error: Optional[str] = None

    def score(self) -> float:
        """Weighted, normalized 0-100 risk score from findings."""
        if not self.findings:
            return 0.0
        total = sum(f.severity.weight for f in self.findings)
        # nonlinear-ish: base 10x count pen skew, cap
        raw = total * 10
        return round(min(100.0, raw), 1)

    def verdict(self) -> Verdict:
        if not self.findings:
            return Verdict.CLEAN
        # Severity-dominant: the worst single finding sets the band. Presence of a
        # high-severity signal matters more than how many low ones accumulate.
        if any(f.severity == Severity.CRITICAL for f in self.findings):
            return Verdict.CRITICAL
        if any(f.severity == Severity.HIGH for f in self.findings):
            return Verdict.HIGH
        if any(f.severity == Severity.MEDIUM for f in self.findings):
            return Verdict.MEDIUM
        return Verdict.LOW

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "score": self.score(),
            "verdict": self.verdict().value,
            "error": self.error,
            "findings": [f.to_dict() for f in self.findings],
        }