"""Data models for apk-signal.

Frozen dataclasses keep signal records immutable once extracted from an APK.
All timestamps are timezone-aware UTC.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class SignalType(str, Enum):
    NETWORK_INDICATOR = "network_indicator"
    HARDCODED_SECRET = "hardcoded_secret"
    PERMISSION = "permission"
    SUSPICIOUS_CAPABILITY = "suspicious_capability"
    NATIVE_LIB = "native_lib"
    STRUCTURE = "structure"


@dataclass(frozen=True)
class Signal:
    """A single extracted signal from an APK."""

    signal_type: SignalType
    severity: Severity
    label: str
    detail: str
    evidence: str = ""
    source_file: str = ""
    score: int = 0

    def to_dict(self) -> dict:
        return {
            "signal_type": self.signal_type.value,
            "severity": self.severity.value,
            "label": self.label,
            "detail": self.detail,
            "evidence": self.evidence,
            "source_file": self.source_file,
            "score": self.score,
        }


@dataclass
class AnalysisResult:
    """Aggregated result for one APK."""

    apk_path: str
    package_name: str = ""
    min_sdk: int | None = None
    target_sdk: int | None = None
    entry_count: int = 0
    dex_count: int = 0
    native_libs: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    signals: List[Signal] = field(default_factory=list)
    scanned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def risk_score(self) -> int:
        """Weighted risk score, capped at 100."""
        raw = sum(s.score for s in self.signals)
        return min(100, raw)

    @property
    def risk_level(self) -> Severity:
        score = self.risk_score
        if score >= 70:
            return Severity.CRITICAL
        if score >= 40:
            return Severity.HIGH
        if score >= 15:
            return Severity.MEDIUM
        if score > 0:
            return Severity.LOW
        return Severity.INFO

    def to_dict(self) -> dict:
        return {
            "apk_path": self.apk_path,
            "package_name": self.package_name,
            "min_sdk": self.min_sdk,
            "target_sdk": self.target_sdk,
            "entry_count": self.entry_count,
            "dex_count": self.dex_count,
            "native_libs": list(self.native_libs),
            "permissions": list(self.permissions),
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "signals": [s.to_dict() for s in self.signals],
            "scanned_at": self.scanned_at.isoformat(),
        }
