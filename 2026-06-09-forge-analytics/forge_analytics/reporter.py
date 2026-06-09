"""Report generation from analytics data."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .analytics import compute_summary, filter_runs, trend_line
from .models import AnalyticsSummary, BuildRun


def generate_markdown_report(
    runs: list[BuildRun],
    reads_total: int = 0,
    reads_errors: int = 0,
    state_dir: str = r"C:\Users\jyot2\jarvis\state",
) -> str:
    """Generate a Markdown analytics report."""
    summary = compute_summary(runs)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = []
    lines.append("# Forge Analytics Report")
    lines.append(f"\nGenerated: {now}")
    lines.append(f"Data source: `{state_dir}`")
    lines.append("")

    # ── Summary ──
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total builds | {summary.total_builds} |")
    lines.append(f"| Successful | {summary.successful_builds} |")
    lines.append(f"| Failed | {summary.failed_builds} |")
    lines.append(f"| Skipped | {summary.skipped_builds} |")
    success_rate = (
        f"{summary.successful_builds / summary.total_builds * 100:.0f}%"
        if summary.total_builds else "N/A"
    )
    lines.append(f"| Success rate | {success_rate} |")
    lines.append(f"")
    lines.append(f"| Cost | Value |")
    lines.append(f"|------|-------|")
    lines.append(f"| Total cost | ${summary.total_cost_usd:.4f} |")
    lines.append(f"| Avg cost/build | ${summary.avg_cost_usd:.4f} |")
    lines.append(f"| Median cost/build | ${summary.median_cost_usd:.4f} |")
    lines.append(f"")
    lines.append(f"| Duration | Value |")
    lines.append(f"|----------|-------|")
    lines.append(f"| Total duration | {_fmt_duration(summary.total_duration_sec)} |")
    lines.append(f"| Avg duration | {_fmt_duration(summary.avg_duration_sec)} |")
    lines.append(f"| Median duration | {_fmt_duration(summary.median_duration_sec)} |")

    if summary.date_range_start and summary.date_range_end:
        lines.append(f"| Date range | {summary.date_range_start} → {summary.date_range_end} |")
    lines.append("")

    # ── Notable builds ──
    if summary.most_expensive or summary.longest:
        lines.append("## Notable Builds")
        lines.append("")
        if summary.most_expensive:
            b = summary.most_expensive
            lines.append(f"- **Most expensive**: `{b.slug}` — ${b.cost_usd:.4f} ({b.duration_sec:.0f}s, {b.status})")
        if summary.longest:
            b = summary.longest
            lines.append(f"- **Longest**: `{b.slug}` — {_fmt_duration(b.duration_sec)} (${b.cost_usd:.4f}, {b.status})")
        lines.append("")

    # ── Error analysis ──
    if summary.error_counts:
        lines.append("## Error Analysis")
        lines.append("")
        lines.append(f"Most common error: `{summary.most_common_error}`")
        lines.append("")
        lines.append("| Error | Count |")
        lines.append("|-------|-------|")
        for err, count in sorted(summary.error_counts.items(), key=lambda x: -x[1])[:10]:
            # Escape pipe characters in error messages
            esc_err = err.replace("|", "\\|")
            lines.append(f"| {esc_err} | {count} |")
        lines.append("")

    # ── Per-date breakdown ──
    if summary.builds_by_date:
        lines.append("## Build Timeline")
        lines.append("")
        lines.append("| Date | Builds | Cost |")
        lines.append("|------|--------|------|")
        for date in sorted(summary.builds_by_date.keys()):
            n = summary.builds_by_date[date]
            cost = summary.cost_by_date.get(date, 0)
            lines.append(f"| {date} | {n} | ${cost:.4f} |")
        lines.append("")

        # Cost trend
        sorted_costs = [summary.cost_by_date[d] for d in sorted(summary.cost_by_date.keys())]
        cost_trend = trend_line(sorted_costs)
        lines.append(f"**Cost trend**: {cost_trend}")
        lines.append("")

        sorted_durations = []
        for d in sorted(summary.builds_by_date.keys()):
            day_runs = [r for r in runs if r.date == d]
            day_dur = [r.duration_sec for r in day_runs if r.duration_sec > 0]
            if day_dur:
                sorted_durations.append(sum(day_dur) / len(day_dur))
        dur_trend = trend_line(sorted_durations)
        lines.append(f"**Duration trend**: {dur_trend}")
        lines.append("")

    # ── Data quality ──
    lines.append("## Data Quality")
    lines.append("")
    lines.append(f"- Total lines read: {reads_total}")
    lines.append(f"- Parse errors: {reads_errors}")
    if reads_total > 0:
        pct = (reads_errors / reads_total) * 100
        lines.append(f"- Error rate: {pct:.1f}%")
    lines.append("")

    # ── Recommendations ──
    lines.append("## Recommendations")
    lines.append("")
    recs = _generate_recommendations(summary)
    if recs:
        for i, rec in enumerate(recs, 1):
            lines.append(f"{i}. {rec}")
    else:
        lines.append("No actionable recommendations at this time.")
    lines.append("")

    return "\n".join(lines)


def _generate_recommendations(s: AnalyticsSummary) -> list[str]:
    """Generate actionable recommendations from summary data."""
    recs: list[str] = []

    if s.total_builds == 0:
        return ["No build data available. Ensure state files exist and are readable."]

    # High failure rate
    fail_rate = s.failed_builds / s.total_builds if s.total_builds else 0
    if fail_rate > 0.3:
        recs.append(
            f"High failure rate ({fail_rate * 100:.0f}%). "
            f"Most common error: `{s.most_common_error}`. Investigate root cause."
        )

    # Rising costs
    sorted_costs = [s.cost_by_date[d] for d in sorted(s.cost_by_date.keys())]
    if trend_line(sorted_costs) == "up":
        recs.append(
            "Build costs are trending upward. Consider reviewing recent spec complexity "
            "or adding cost caps to prevent budget overruns."
        )

    # Rising duration
    if s.avg_duration_sec > 600:
        recs.append(
            f"Average build duration is {_fmt_duration(s.avg_duration_sec)}, "
            f"exceeding 10 minutes. Consider parallelizing or scoping down builds."
        )

    # Expensive outlier
    if s.most_expensive and s.avg_cost_usd > 0:
        ratio = s.most_expensive.cost_usd / s.avg_cost_usd
        if ratio > 2:
            recs.append(
                f"`{s.most_expensive.slug}` cost {ratio:.0f}x the average. "
                f"Review if this build's scope was appropriate."
            )

    # Skipped builds
    if s.skipped_builds > 0:
        recs.append(
            f"{s.skipped_builds} build(s) were skipped (likely budget). "
            f"Consider reducing per-build costs or increasing the daily budget."
        )

    return recs


def _fmt_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}m"
    hours = minutes / 60
    return f"{hours:.1f}h"
