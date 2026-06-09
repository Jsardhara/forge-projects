"""Analytics computation over build run data."""
from __future__ import annotations

import statistics
from collections import Counter
from datetime import datetime
from typing import Optional

from .models import AnalyticsSummary, BuildRun


def compute_summary(runs: list[BuildRun]) -> AnalyticsSummary:
    """Compute analytics summary from a list of build runs."""
    if not runs:
        return AnalyticsSummary(
            total_builds=0, successful_builds=0, failed_builds=0,
            skipped_builds=0, total_cost_usd=0, avg_cost_usd=0,
            median_cost_usd=0, total_duration_sec=0, avg_duration_sec=0,
            median_duration_sec=0, most_expensive=None, longest=None,
            most_common_error=None, error_counts={}, builds_by_date={},
            cost_by_date={}, date_range_start=None, date_range_end=None,
        )

    successful = [r for r in runs if r.status == "success"]
    failed = [r for r in runs if r.status in ("failed", "error")]
    skipped = [r for r in runs if r.status.startswith("skip")]

    costs = [r.cost_usd for r in runs if r.cost_usd > 0]
    durations = [r.duration_sec for r in runs if r.duration_sec > 0]

    # Most expensive and longest
    most_expensive = max(runs, key=lambda r: r.cost_usd) if costs else None
    longest = max(runs, key=lambda r: r.duration_sec) if durations else None

    # Error frequency
    error_counts: dict[str, int] = Counter()
    for r in runs:
        if r.error:
            # Truncate long error messages for grouping
            key = r.error[:120] if len(r.error) > 120 else r.error
            error_counts[key] += 1

    most_common_error = None
    if error_counts:
        most_common_error = error_counts.most_common(1)[0][0]

    # Builds by date
    builds_by_date: dict[str, int] = Counter()
    cost_by_date: dict[str, float] = {}
    for r in runs:
        d = r.date or "unknown"
        builds_by_date[d] += 1
        cost_by_date[d] = cost_by_date.get(d, 0) + r.cost_usd

    # Date range
    dates = sorted([r.date for r in runs if r.date])
    date_range_start = dates[0] if dates else None
    date_range_end = dates[-1] if dates else None

    total_cost = sum(costs) if costs else 0
    total_duration = sum(durations) if durations else 0

    return AnalyticsSummary(
        total_builds=len(runs),
        successful_builds=len(successful),
        failed_builds=len(failed),
        skipped_builds=len(skipped),
        total_cost_usd=round(total_cost, 4),
        avg_cost_usd=round(statistics.mean(costs), 4) if costs else 0,
        median_cost_usd=round(statistics.median(costs), 4) if costs else 0,
        total_duration_sec=round(total_duration, 1),
        avg_duration_sec=round(statistics.mean(durations), 1) if durations else 0,
        median_duration_sec=round(statistics.median(durations), 1) if durations else 0,
        most_expensive=most_expensive,
        longest=longest,
        most_common_error=most_common_error,
        error_counts=dict(error_counts),
        builds_by_date=dict(builds_by_date),
        cost_by_date={k: round(v, 4) for k, v in cost_by_date.items()},
        date_range_start=date_range_start,
        date_range_end=date_range_end,
    )


def filter_runs(
    runs: list[BuildRun],
    since: Optional[str] = None,
    until: Optional[str] = None,
    status: Optional[str] = None,
) -> list[BuildRun]:
    """Filter build runs by date range and/or status."""
    result = runs
    if since:
        result = [r for r in result if r.date >= since]
    if until:
        result = [r for r in result if r.date <= until]
    if status:
        result = [r for r in result if r.status == status]
    return result


def trend_line(values: list[float]) -> str:
    """Return a simple trend indicator: 'up', 'down', or 'flat'."""
    if len(values) < 3:
        return "insufficient_data"
    # Compare first half avg vs second half avg
    mid = len(values) // 2
    first_half = statistics.mean(values[:mid])
    second_half = statistics.mean(values[mid:])
    diff_pct = ((second_half - first_half) / first_half * 100) if first_half else 0
    if diff_pct > 10:
        return "up"
    elif diff_pct < -10:
        return "down"
    return "flat"
