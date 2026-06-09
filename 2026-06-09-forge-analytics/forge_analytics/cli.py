"""CLI for forge-analytics."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click

from .analytics import compute_summary, filter_runs
from .models import BuildRun
from .readers import read_build_runs, read_forge_runs
from .reporter import generate_markdown_report


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Forge Analytics — Build pipeline intelligence for Jarmes."""
    pass


@main.command()
@click.option(
    "--state-dir",
    default=r"C:\Users\jyot2\jarvis\state",
    help="Path to Jarmes state directory",
)
@click.option("--since", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--until", default=None, help="End date (YYYY-MM-DD)")
@click.option("--status", default=None, help="Filter by status (success/failed/skipped)")
@click.option("--output", "-o", default=None, help="Output file path (default: stdout)")
@click.option("--json-output", is_flag=True, default=False, help="Output JSON instead of Markdown")
def report(state_dir: str, since: Optional[str], until: Optional[str],
           status: Optional[str], output: Optional[str], json_output: bool):
    """Generate an analytics report from build run data."""
    daily_projects_path = Path(state_dir) / "daily_projects.jsonl"

    runs, total, errs = read_build_runs(daily_projects_path)

    # Apply filters
    if since or until or status:
        runs = filter_runs(runs, since=since, until=until, status=status)

    if json_output:
        summary = compute_summary(runs)
        # Convert to dict for JSON serialization
        data = {
            "total_builds": summary.total_builds,
            "successful_builds": summary.successful_builds,
            "failed_builds": summary.failed_builds,
            "skipped_builds": summary.skipped_builds,
            "total_cost_usd": summary.total_cost_usd,
            "avg_cost_usd": summary.avg_cost_usd,
            "median_cost_usd": summary.median_cost_usd,
            "total_duration_sec": summary.total_duration_sec,
            "avg_duration_sec": summary.avg_duration_sec,
            "median_duration_sec": summary.median_duration_sec,
            "date_range_start": summary.date_range_start,
            "date_range_end": summary.date_range_end,
            "error_counts": summary.error_counts,
            "builds_by_date": summary.builds_by_date,
            "cost_by_date": summary.cost_by_date,
        }
        result = json.dumps(data, indent=2, default=str)
    else:
        result = generate_markdown_report(
            runs, reads_total=total, reads_errors=errs, state_dir=state_dir
        )

    if output:
        Path(output).write_text(result, encoding="utf-8")
        click.echo(f"Report written to {output}")
    else:
        click.echo(result)


@main.command()
@click.option(
    "--state-dir",
    default=r"C:\Users\jyot2\jarvis\state",
    help="Path to Jarmes state directory",
)
def status(state_dir: str):
    """Quick status: show latest build and overall health."""
    daily_projects_path = Path(state_dir) / "daily_projects.jsonl"
    runs, total, errs = read_build_runs(daily_projects_path)

    if not runs:
        click.echo("No build data found.")
        return

    latest = max(runs, key=lambda r: r.date or "")
    click.echo(f"Latest build: {latest.date} — {latest.slug} ({latest.status})")
    click.echo(f"  Cost: ${latest.cost_usd:.4f} | Duration: {latest.duration_sec:.0f}s")

    successful = [r for r in runs if r.status == "success"]
    failed = [r for r in runs if r.status in ("failed", "error")]
    click.echo(f"\nOverall: {len(runs)} builds | {len(successful)} success | {len(failed)} failed")

    total_cost = sum(r.cost_usd for r in runs)
    click.echo(f"Total cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
