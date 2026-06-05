"""Aggregator — groups parsed log entries into health summaries."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Optional

from healthpulse.models import (
    ErrorPattern,
    HealthStatus,
    JobHealth,
    LogEntry,
    SystemHealth,
)
from healthpulse.parser import get_default_log_paths, parse_file
from healthpulse.suggester import KNOWN_FIXES


def _error_signature(message: str, traceback: Optional[str] = None) -> str:
    """Create a normalized error signature for grouping."""
    # Use the exception type + message as the signature
    sig = message.strip()
    if traceback:
        # Extract the last line of the traceback (the exception)
        tb_lines = [l for l in traceback.split("\n") if l.strip() and not l.strip().startswith("File ") and not l.strip().startswith("  File ")]
        if tb_lines:
            sig = tb_lines[-1].strip()
    # Normalize: remove specific values (IDs, paths, numbers)
    import re
    sig = re.sub(r"0x[0-9a-fA-F]+", "<addr>", sig)
    sig = re.sub(r"\d+", "<n>", sig)
    return sig[:200]


def aggregate_jobs(entries: list[LogEntry]) -> list[JobHealth]:
    """Aggregate log entries into per-job health summaries."""
    job_data: dict[str, dict] = defaultdict(lambda: {
        "runs": 0, "errors": 0, "successes": 0,
        "last_error": None, "last_error_time": None,
        "last_success_time": None, "first_seen": None,
        "error_signatures": defaultdict(lambda: {"count": 0, "sample": "", "first": None, "last": None}),
    })

    for entry in entries:
        if not entry.job_name:
            continue

        jd = job_data[entry.job_name]

        # Track first seen
        if entry.timestamp and (jd["first_seen"] is None or entry.timestamp < jd["first_seen"]):
            jd["first_seen"] = entry.timestamp

        # Count runs (any mention of the job)
        if "Running job" in entry.message:
            jd["runs"] += 1

        # Count successes
        if entry.is_success:
            jd["successes"] += 1
            if entry.timestamp:
                jd["last_success_time"] = entry.timestamp

        # Count errors
        if entry.is_error and entry.job_name:
            jd["errors"] += 1
            if entry.timestamp:
                jd["last_error_time"] = entry.timestamp
            jd["last_error"] = entry.message[:300]

            # Track error signature
            sig = _error_signature(entry.message, entry.traceback)
            es = jd["error_signatures"][sig]
            es["count"] += 1
            if not es["sample"]:
                es["sample"] = entry.message[:200]
            if entry.timestamp:
                if es["first"] is None or entry.timestamp < es["first"]:
                    es["first"] = entry.timestamp
                es["last"] = entry.timestamp

    results = []
    for name, jd in sorted(job_data.items()):
        total = jd["errors"] + jd["successes"]
        error_rate = jd["errors"] / total if total > 0 else 0.0

        # Determine status
        if total == 0:
            status = HealthStatus.UNKNOWN
        elif error_rate == 0:
            status = HealthStatus.HEALTHY
        elif error_rate < 0.3:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.FAILING

        # Top errors
        top_errors = sorted(
            [{"signature": k, **v} for k, v in jd["error_signatures"].items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:5]

        # Get suggestion for top error
        suggestion = None
        if top_errors:
            top_sig = top_errors[0]["signature"]
            for pattern, fix in KNOWN_FIXES.items():
                if pattern.lower() in top_sig.lower():
                    suggestion = fix
                    break

        results.append(JobHealth(
            name=name,
            status=status,
            total_runs=jd["runs"],
            total_errors=jd["errors"],
            total_successes=jd["successes"],
            error_rate=round(error_rate, 3),
            last_error=jd["last_error"],
            last_error_time=jd["last_error_time"],
            last_success_time=jd["last_success_time"],
            first_seen=jd["first_seen"],
            top_errors=top_errors,
            suggestion=suggestion,
        ))

    return results


def aggregate_error_patterns(entries: list[LogEntry]) -> list[ErrorPattern]:
    """Find recurring error patterns across all entries."""
    patterns: dict[str, dict] = defaultdict(lambda: {
        "count": 0, "first": None, "last": None,
        "sample": "", "job_name": None,
    })

    for entry in entries:
        if not entry.is_error:
            continue

        sig = _error_signature(entry.message, entry.traceback)
        p = patterns[sig]
        p["count"] += 1
        if not p["sample"]:
            p["sample"] = entry.message[:200]
        if entry.job_name:
            p["job_name"] = entry.job_name
        if entry.timestamp:
            if p["first"] is None or entry.timestamp < p["first"]:
                p["first"] = entry.timestamp
            p["last"] = entry.timestamp

    results = []
    for sig, data in sorted(patterns.items(), key=lambda x: x[1]["count"], reverse=True):
        suggestion = None
        for pattern, fix in KNOWN_FIXES.items():
            if pattern.lower() in sig.lower():
                suggestion = fix
                break

        results.append(ErrorPattern(
            pattern=sig[:150],
            count=data["count"],
            first_seen=data["first"],
            last_seen=data["last"],
            sample_message=data["sample"],
            job_name=data["job_name"],
            suggestion=suggestion,
        ))

    return results[:20]  # Top 20


def build_system_health(
    log_paths: Optional[list[str]] = None,
    max_lines: int = 5000,
) -> SystemHealth:
    """Build a complete system health snapshot from log files."""
    if log_paths is None:
        log_paths = [str(p) for p in get_default_log_paths()]

    all_entries: list[LogEntry] = []
    sources = []
    total_errors = 0
    total_warnings = 0

    for path in log_paths:
        entries = parse_file(path, max_lines=max_lines)
        if entries:
            sources.append(str(path))
            all_entries.extend(entries)
            for e in entries:
                if e.is_error:
                    total_errors += 1
                elif e.level == "WARNING":
                    total_warnings += 1

    jobs = aggregate_jobs(all_entries)
    error_patterns = aggregate_error_patterns(all_entries)

    # Overall status
    if not jobs:
        overall = HealthStatus.UNKNOWN
    elif any(j.status == HealthStatus.FAILING for j in jobs):
        overall = HealthStatus.FAILING
    elif any(j.status == HealthStatus.DEGRADED for j in jobs):
        overall = HealthStatus.DEGRADED
    elif all(j.status == HealthStatus.HEALTHY for j in jobs):
        overall = HealthStatus.HEALTHY
    else:
        overall = HealthStatus.UNKNOWN

    return SystemHealth(
        log_sources=sources,
        total_lines_parsed=len(all_entries),
        total_errors=total_errors,
        total_warnings=total_warnings,
        jobs=jobs,
        top_error_patterns=error_patterns,
        overall_status=overall,
    )
