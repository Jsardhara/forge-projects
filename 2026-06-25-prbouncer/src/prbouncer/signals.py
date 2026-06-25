"""Individual spam detection signals.

Each signal returns a SpamSignal with a raw_score (0.0–1.0) indicating how
strongly this specific signal indicates spam, and evidence explaining why.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from prbouncer.models import PullRequest, AuthorProfile, SpamSignal, SignalType


# --- AI slop markers found in low-quality AI-generated PRs ---
AI_SLOP_PHRASES: tuple[str, ...] = (
    "I have analyzed the codebase",
    "I've analyzed the codebase",
    "this PR improves the codebase",
    "here is the improved version",
    "here is a refactored version",
    "I have refactored the code",
    "I've refactored the code",
    "this change improves code quality",
    "this change enhances",
    "I noticed that the code",
    "I noticed that there is",
    "as a helpful assistant",
    "as an AI",
    "I am an AI",
    "I went ahead and",
    "I have also updated",
    "I have made the following changes",
    "sure! here",
    "here you go",
    "Certainly! I",
    "Of course! I",
    "Let me refactor",
)

# Generic PR titles that indicate low effort
GENERIC_TITLE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^update\s+\w+\.py$", re.IGNORECASE),
    re.compile(r"^fix\s*$", re.IGNORECASE),
    re.compile(r"^fix\s+\w+$", re.IGNORECASE),
    re.compile(r"^update", re.IGNORECASE),
    re.compile(r"^changes?$", re.IGNORECASE),
    re.compile(r"^wip$", re.IGNORECASE),
    re.compile(r"^patch$", re.IGNORECASE),
    re.compile(r"^minor\s+fix(es)?$", re.IGNORECASE),
    re.compile(r"^code\s+(cleanup|improvement|quality)", re.IGNORECASE),
    re.compile(r"^refactor(\s+\w+)?$", re.IGNORECASE),
)

# File paths that are suspicious in spam PRs
SUSPICIOUS_FILE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"README\.md$", re.IGNORECASE),
    re.compile(r"CONTRIBUTING\.md$", re.IGNORECASE),
    re.compile(r"\.github/.*", re.IGNORECASE),
    re.compile(r"docs/.*\.md$", re.IGNORECASE),
    re.compile(r"package\.json$", re.IGNORECASE),
    re.compile(r"pyproject\.toml$", re.IGNORECASE),
    re.compile(r"setup\.py$", re.IGNORECASE),
    re.compile(r"setup\.cfg$", re.IGNORECASE),
)


def signal_new_account(pr: PullRequest) -> SpamSignal:
    """New accounts (<7 days) are suspicious. Very new (<1 day) is highly suspicious."""
    age = pr.author.account_age_days
    if age < 1:
        raw = 1.0
        evidence = f"Account is {age} days old (created today)"
    elif age < 7:
        raw = 0.7 + 0.3 * (1 - age / 7)
        evidence = f"Account is {age} days old (< 7 day threshold)"
    elif age < 30:
        raw = 0.3 * (1 - (age - 7) / 23)
        evidence = f"Account is {age} days old (< 30 days, reduced weight)"
    else:
        raw = 0.0
        evidence = f"Account is {age} days old (established)"

    return SpamSignal(
        signal_type=SignalType.NEW_ACCOUNT,
        weight=0.20,
        triggered=raw > 0.0,
        evidence=evidence,
        raw_score=raw,
    )


def signal_no_linked_issue(pr: PullRequest) -> SpamSignal:
    """PRs without linked issues are often drive-by contributions."""
    if pr.linked_issues > 0:
        return SpamSignal(
            signal_type=SignalType.NO_LINKED_ISSUE,
            weight=0.15,
            triggered=False,
            evidence=f"Has {pr.linked_issues} linked issue(s)",
            raw_score=0.0,
        )

    # Check if body/title references an issue manually
    if pr.has_issue_ref:
        return SpamSignal(
            signal_type=SignalType.NO_LINKED_ISSUE,
            weight=0.15,
            triggered=False,
            evidence="References issue number in title/body (manual ref)",
            raw_score=0.0,
        )

    return SpamSignal(
        signal_type=SignalType.NO_LINKED_ISSUE,
        weight=0.15,
        triggered=True,
        evidence="No linked issue and no issue reference in title/body",
        raw_score=0.8,
    )


def signal_large_diff(pr: PullRequest) -> SpamSignal:
    """Very large diffs from new contributors are suspicious."""
    lines = pr.total_lines
    age = pr.author.account_age_days

    # Thresholds differ by account age
    if age < 30:
        threshold = 500
    elif age < 365:
        threshold = 2000
    else:
        threshold = 5000

    if lines > threshold * 2:
        raw = 1.0
        evidence = f"{lines} lines changed (>{threshold * 2} for {age}d-old account)"
    elif lines > threshold:
        raw = 0.5 + 0.5 * (lines - threshold) / threshold
        evidence = f"{lines} lines changed (>{threshold} for {age}d-old account)"
    else:
        raw = 0.0
        evidence = f"{lines} lines changed (within {threshold} threshold)"

    return SpamSignal(
        signal_type=SignalType.LARGE_DIFF,
        weight=0.10,
        triggered=raw > 0.0,
        evidence=evidence,
        raw_score=raw,
    )


def signal_ai_slop(pr: PullRequest) -> SpamSignal:
    """Detect AI slop markers in PR body."""
    body_lower = pr.body.lower()
    matches: list[str] = []

    for phrase in AI_SLOP_PHRASES:
        if phrase.lower() in body_lower:
            matches.append(phrase)

    if not matches:
        return SpamSignal(
            signal_type=SignalType.AI_SLOP_MARKERS,
            weight=0.25,
            triggered=False,
            evidence="No AI slop markers detected",
            raw_score=0.0,
        )

    raw = min(1.0, 0.4 + 0.2 * len(matches))
    found = "; ".join(matches[:3])
    if len(matches) > 3:
        found += f" (+{len(matches) - 3} more)"

    return SpamSignal(
        signal_type=SignalType.AI_SLOP_MARKERS,
        weight=0.25,
        triggered=True,
        evidence=f"AI slop phrases found: {found}",
        raw_score=raw,
    )


def signal_generic_title(pr: PullRequest) -> SpamSignal:
    """Generic PR titles indicate low effort / AI-generated content."""
    title = pr.title.strip()

    for pattern in GENERIC_TITLE_PATTERNS:
        if pattern.match(title):
            return SpamSignal(
                signal_type=SignalType.GENERIC_TITLE,
                weight=0.12,
                triggered=True,
                evidence=f"Title '{title}' matches generic pattern '{pattern.pattern}'",
                raw_score=0.7,
            )

    # Very short titles are also suspicious
    if len(title) < 10:
        return SpamSignal(
            signal_type=SignalType.GENERIC_TITLE,
            weight=0.12,
            triggered=True,
            evidence=f"Title too short: '{title}' ({len(title)} chars)",
            raw_score=0.5,
        )

    # Title is just a filepath
    if "/" in title and not any(c in title for c in "(:-"):
        return SpamSignal(
            signal_type=SignalType.GENERIC_TITLE,
            weight=0.12,
            triggered=True,
            evidence=f"Title looks like a filepath: '{title}'",
            raw_score=0.6,
        )

    return SpamSignal(
        signal_type=SignalType.GENERIC_TITLE,
        weight=0.12,
        triggered=False,
        evidence=f"Title '{title}' is specific enough",
        raw_score=0.0,
    )


def signal_rapid_fire(pr: PullRequest, recent_pr_count: int = 0) -> SpamSignal:
    """Author submitting many PRs in a short window."""
    if recent_pr_count > 10:
        raw = 1.0
        evidence = f"Author has {recent_pr_count} recent PRs (>10 threshold)"
    elif recent_pr_count > 5:
        raw = 0.5 + 0.5 * (recent_pr_count - 5) / 5
        evidence = f"Author has {recent_pr_count} recent PRs (>5 threshold)"
    elif recent_pr_count > 2:
        raw = 0.2 * (recent_pr_count - 2) / 3
        evidence = f"Author has {recent_pr_count} recent PRs (>2, mild signal)"
    else:
        raw = 0.0
        evidence = f"Author has {recent_pr_count} recent PRs (normal)"

    return SpamSignal(
        signal_type=SignalType.RAPID_FIRE,
        weight=0.15,
        triggered=raw > 0.0,
        evidence=evidence,
        raw_score=raw,
    )


def signal_low_engagement(pr: PullRequest) -> SpamSignal:
    """PRs with zero comments/reviews from the author are suspicious for new accounts."""
    if pr.author.account_age_days > 365:
        return SpamSignal(
            signal_type=SignalType.LOW_ENGAGEMENT,
            weight=0.05,
            triggered=False,
            evidence="Established contributor, engagement signal skipped",
            raw_score=0.0,
        )

    if pr.comment_count == 0 and pr.review_count == 0:
        raw = 0.6 if pr.author.account_age_days < 30 else 0.3
        return SpamSignal(
            signal_type=SignalType.LOW_ENGAGEMENT,
            weight=0.05,
            triggered=True,
            evidence="Zero comments and reviews on PR from new account",
            raw_score=raw,
        )

    return SpamSignal(
        signal_type=SignalType.LOW_ENGAGEMENT,
        weight=0.05,
        triggered=False,
        evidence=f"Has {pr.comment_count} comments, {pr.review_count} reviews",
        raw_score=0.0,
    )


def signal_suspicious_files(pr: PullRequest) -> SpamSignal:
    """PRs that only touch documentation/config files are often spam."""
    if not pr.file_paths:
        return SpamSignal(
            signal_type=SignalType.SUSPICIOUS_FILES,
            weight=0.08,
            triggered=False,
            evidence="No file paths provided, signal skipped",
            raw_score=0.0,
        )

    suspicious_count = 0
    total = len(pr.file_paths)
    for fpath in pr.file_paths:
        for pattern in SUSPICIOUS_FILE_PATTERNS:
            if pattern.search(fpath):
                suspicious_count += 1
                break

    if total == 0:
        ratio = 0.0
    else:
        ratio = suspicious_count / total

    # All files are suspicious docs/config
    if ratio >= 1.0 and pr.author.account_age_days < 30:
        raw = 0.8
        evidence = f"All {total} files are docs/config (new account)"
    elif ratio >= 0.8:
        raw = 0.5
        evidence = f"{suspicious_count}/{total} files are docs/config"
    elif ratio > 0.5:
        raw = 0.3
        evidence = f"{suspicious_count}/{total} files are docs/config (mixed)"
    else:
        raw = 0.0
        evidence = f"{suspicious_count}/{total} files are docs/config (minor)"

    return SpamSignal(
        signal_type=SignalType.SUSPICIOUS_FILES,
        weight=0.08,
        triggered=raw > 0.0,
        evidence=evidence,
        raw_score=raw,
    )


def signal_account_pattern(pr: PullRequest) -> SpamSignal:
    """Detect bot-like account patterns (username patterns, no engagement)."""
    username = pr.author.username
    indicators: list[str] = []
    raw = 0.0

    # Generated usernames: word-word-NNNN or word_NNNNN
    if re.match(r"^[a-z]+[-_]\d{4,}$", username, re.IGNORECASE):
        raw += 0.4
        indicators.append("username matches generated pattern (word-digits)")

    # Very long usernames with numbers
    if len(username) > 20 and sum(c.isdigit() for c in username) > 5:
        raw += 0.3
        indicators.append("long username with many digits")

    # No bio AND no profile pic AND low followers
    if not pr.author.has_bio and not pr.author.has_profile_pic and pr.author.followers < 3:
        raw += 0.3
        indicators.append("no bio, no profile pic, <3 followers")

    raw = min(1.0, raw)

    if indicators:
        return SpamSignal(
            signal_type=SignalType.ACCOUNT_PATTERN,
            weight=0.10,
            triggered=True,
            evidence="; ".join(indicators),
            raw_score=raw,
        )

    return SpamSignal(
        signal_type=SignalType.ACCOUNT_PATTERN,
        weight=0.10,
        triggered=False,
        evidence="No bot-like patterns detected",
        raw_score=0.0,
    )
