"""Exposure scoring engine.

Combines breach records for one identity into a 0-100 exposure score and a
Severity bucket, plus a list of the most sensitive breach types present.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from breach_sentinel.models import (
    BreachRecord,
    BreachType,
    ExposureScore,
    SENSITIVITY_WEIGHT,
    Severity,
)


def score_exposure(iid: str, records: Iterable[BreachRecord]) -> ExposureScore:
    recs = list(records)
    if not recs:
        return ExposureScore(
            iid=iid,
            score=0,
            severity=Severity.INFO,
            record_count=0,
            critical_types=[],
            latest_breach=None,
            notes=["No exposure detected."],
        )

    # Base from how many breaches + how sensitive the leaked types are.
    sensitivity = sum(SENSITIVITY_WEIGHT.get(r.breach_type, 2) for r in recs)
    # 5 points per breach record (cap at 35), sensitivity scaled (cap at 55).
    breach_points = min(35, len(recs) * 5)
    sensitivity_points = min(55, sensitivity * 5)

    # Recency multiplier: breaches in the last 90 days add up to +10.
    now = datetime.now(timezone.utc)
    recency_bonus = 0
    latest: datetime | None = None
    for r in recs:
        if r.breach_date:
            if latest is None or r.breach_date > latest:
                latest = r.breach_date
            age_days = (now - r.breach_date).days
            if 0 <= age_days <= 90:
                recency_bonus += 2
    recency_bonus = min(10, recency_bonus)

    score = min(100, breach_points + sensitivity_points + recency_bonus)

    # Critical types = anything with sensitivity >= SSN/passport weight (8).
    critical_types = sorted(
        {r.breach_type for r in recs if SENSITIVITY_WEIGHT.get(r.breach_type, 2) >= 8},
        key=lambda t: SENSITIVITY_WEIGHT[t],
        reverse=True,
    )
    has_password = any(r.breach_type == BreachType.PASSWORD for r in recs)

    # Severity buckets. Identity documents are always CRITICAL; a leaked
    # password is at least MEDIUM (a real credential compromise).
    if critical_types:
        severity = Severity.CRITICAL
        score = max(score, 80)
    elif score >= 80:
        severity = Severity.CRITICAL
    elif has_password or score >= 60:
        severity = Severity.HIGH
        if has_password:
            score = max(score, 35)
    elif score >= 35:
        severity = Severity.MEDIUM
    elif score >= 10:
        severity = Severity.LOW
    else:
        severity = Severity.INFO
        if has_password:
            # A password in any breach is actionable even if old.
            severity = Severity.MEDIUM
            score = max(score, 35)

    notes = [
        f"{len(recs)} breach record(s) across {len(set(r.source_id for r in recs))} source(s).",
        "Identity documents (SSN/passport) exposed." if critical_types else "No identity documents exposed.",
    ]
    if latest:
        notes.append(f"Most recent breach: {latest.date().isoformat()}.")

    return ExposureScore(
        iid=iid,
        score=score,
        severity=severity,
        record_count=len(recs),
        critical_types=critical_types,
        latest_breach=latest,
        notes=notes,
    )


def severity_rank(severity: Severity) -> int:
    return severity.rank
