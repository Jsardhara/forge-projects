"""Data models for PRBouncer."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


class SignalType(enum.Enum):
    """Categories of spam signals."""

    NEW_ACCOUNT = "new_account"
    NO_LINKED_ISSUE = "no_linked_issue"
    LARGE_DIFF = "large_diff"
    AI_SLOP_MARKERS = "ai_slop_markers"
    GENERIC_TITLE = "generic_title"
    RAPID_FIRE = "rapid_fire"
    LOW_ENGAGEMENT = "low_engagement"
    SUSPICIOUS_FILES = "suspicious_files"
    REPEATED_CONTENT = "repeated_content"
    ACCOUNT_PATTERN = "account_pattern"


@dataclass(frozen=True)
class AuthorProfile:
    """GitHub author profile data relevant to spam detection."""

    username: str
    account_age_days: int
    followers: int = 0
    following: int = 0
    public_repos: int = 0
    pr_count_total: int = 0
    pr_count_to_target_repo: int = 0
    has_bio: bool = False
    has_profile_pic: bool = False

    @property
    def is_new(self) -> bool:
        """Account created less than 7 days ago."""
        return self.account_age_days < 7

    @property
    def is_likely_bot(self) -> bool:
        """Heuristic: new account, no bio, no profile pic, high PR volume."""
        return (
            self.account_age_days < 30
            and not self.has_bio
            and not self.has_profile_pic
            and self.pr_count_total > 10
        )


@dataclass(frozen=True)
class PullRequest:
    """Pull request data for spam analysis."""

    pr_number: int
    title: str
    body: str
    author: AuthorProfile
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    changed_files: int = 0
    additions: int = 0
    deletions: int = 0
    linked_issues: int = 0
    commits: int = 1
    is_draft: bool = False
    labels: tuple[str, ...] = ()
    file_paths: tuple[str, ...] = ()
    comment_count: int = 0
    review_count: int = 0

    @property
    def total_lines(self) -> int:
        return self.additions + self.deletions

    @property
    def has_issue_ref(self) -> bool:
        """Title or body references an issue number (e.g., 'Fixes #123')."""
        import re

        text = f"{self.title} {self.body}"
        return bool(re.search(r"#\d+", text)) or self.linked_issues > 0


@dataclass(frozen=True)
class SpamSignal:
    """A single spam detection signal with weight and evidence."""

    signal_type: SignalType
    weight: float
    triggered: bool
    evidence: str
    raw_score: float = 0.0

    @property
    def contribution(self) -> float:
        """Weighted contribution of this signal."""
        return self.weight * self.raw_score if self.triggered else 0.0


@dataclass(frozen=True)
class Verdict:
    """Final spam assessment for a pull request."""

    pr_number: int
    spam_probability: float
    signals: tuple[SpamSignal, ...] = ()
    label: str = ""

    LEGIT_THRESHOLD = 0.25
    SPAM_THRESHOLD = 0.65

    @property
    def classification(self) -> str:
        if self.spam_probability < self.LEGIT_THRESHOLD:
            return "LEGIT"
        elif self.spam_probability > self.SPAM_THRESHOLD:
            return "SPAM"
        else:
            return "SUSPICIOUS"

    @property
    def triggered_signals(self) -> tuple[SpamSignal, ...]:
        return tuple(s for s in self.signals if s.triggered)

    @property
    def explain(self) -> str:
        """Human-readable explanation of the verdict."""
        lines = [f"PR #{self.pr_number}: {self.classification} (p={self.spam_probability:.3f})"]
        for s in self.triggered_signals:
            lines.append(f"  - [{s.signal_type.value}] {s.evidence} (score={s.raw_score:.2f}, weight={s.weight:.2f})")
        if not self.triggered_signals:
            lines.append("  (no signals triggered)")
        return "\n".join(lines)
