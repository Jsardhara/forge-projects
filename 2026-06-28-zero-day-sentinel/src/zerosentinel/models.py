"""Data models for ZeroDaySentinel."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Severity(Enum):
    """Vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "unknown"


@dataclasses.dataclass(frozen=True)
class ExploitRepositry:
    """Represents a detected exploit/0-day repository on GitHub."""
    repo_id: str
    repo_url: str
    owner: str
    name: str
    description: str
    published_at: datetime
    topics: tuple[str, ...]
    stars: int
    language: str
    raw_readme: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> ExploitRepositry:
        """Parse from GitHub API response dict."""
        published = data.get("published_at")
        if published:
            pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        else:
            pub_dt = datetime.now(timezone.utc)

        return cls(
            repo_id=data.get("repo_id", ""),
            repo_url=data.get("repo_url", ""),
            owner=data.get("owner", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            published_at=pub_dt,
            topics=tuple(data.get("topics", ())),
            stars=data.get("stars", 0),
            language=data.get("language", ""),
            raw_readme=data.get("raw_readme", ""),
        )


@dataclasses.dataclass(frozen=True)
class VulnerabilityFingerprint:
    """Extracted vulnerability fingerprint from an exploit repository."""
    cve_id: Optional[str]
    affected_product: str
    affected_versions: tuple[str, ...]
    vulnerability_type: str
    severity: Severity
    summary: str
    extracted_cpes: tuple[str, ...] = ()
    references: tuple[str, ...] = ()

    @property
    def is_critical(self) -> bool:
        return self.severity == Severity.CRITICAL

    @property
    def fingerprint_key(self) -> str:
        """Unique key for deduplication."""
        return f"{self.affected_product}:{self.vulnerability_type}:{self.cve_id or 'unknown'}"


@dataclasses.dataclass(frozen=True)
class PatchSuggestion:
    """AI-assisted patch suggestion for a detected vulnerability."""
    fingerprint: VulnerabilityFingerprint
    confidence: float  # 0.0 - 1.0
    suggested_fix: str
    patch_type: str  # "version_pin", "config_change", "code_fix", "workaround"
    references: tuple[str, ...] = ()
    estimated_effort: str = "medium"  # low, medium, high

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.7


@dataclasses.dataclass(frozen=True)
class DetectionResult:
    """Result of scanning for 0-day exploits matching a dependency graph."""
    scan_timestamp: datetime
    repos_scanned: int
    matches: tuple[VulnerabilityFingerprint, ...]
    patch_suggestions: tuple[PatchSuggestion, ...]
    scan_duration_seconds: float

    @property
    def has_matches(self) -> bool:
        return len(self.matches) > 0

    @property
    def critical_count(self) -> int:
        return sum(1 for m in self.matches if m.is_critical)
