"""Data models for forge-analytics."""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from typing import Optional


@dataclasses.dataclass
class BuildRun:
    """Represents a single build run from daily_projects.jsonl."""
    date: str
    slug: str
    title: str
    folder: str
    repo_url: str
    commit_sha: str
    cost_usd: float
    duration_sec: float
    status: str
    error: Optional[str]
    timestamp: Optional[datetime] = None

    @classmethod
    def from_json(cls, data: dict) -> "BuildRun":
        ts = None
        raw_ts = data.get("ts")
        if raw_ts:
            try:
                ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        return cls(
            date=data.get("date", ""),
            slug=data.get("slug", ""),
            title=data.get("title", ""),
            folder=data.get("folder", ""),
            repo_url=data.get("repo_url", ""),
            commit_sha=data.get("commit_sha", ""),
            cost_usd=float(data.get("cost_usd", 0) or 0),
            duration_sec=float(data.get("duration_sec", 0) or 0),
            status=data.get("status", "unknown"),
            error=data.get("error"),
            timestamp=ts,
        )


@dataclasses.dataclass
class ForgeRunEntry:
    """Represents a single entry from forge_runs.jsonl."""
    run_id: str
    repo_path: str
    branch: str
    task: str

    @classmethod
    def from_json(cls, data: dict) -> "ForgeRunEntry":
        return cls(
            run_id=data.get("run_id", ""),
            repo_path=data.get("repo_path", ""),
            branch=data.get("branch", ""),
            task=data.get("task", "")[:200],  # truncate long task descriptions
        )


@dataclasses.dataclass
class CostEntry:
    """Represents a single entry from cost_log.jsonl."""
    timestamp: Optional[datetime]
    agent: str
    action: str
    cost_usd: float
    details: Optional[str]


@dataclasses.dataclass
class AnalyticsSummary:
    """Computed analytics over a set of build runs."""
    total_builds: int
    successful_builds: int
    failed_builds: int
    skipped_builds: int
    total_cost_usd: float
    avg_cost_usd: float
    median_cost_usd: float
    total_duration_sec: float
    avg_duration_sec: float
    median_duration_sec: float
    most_expensive: Optional[BuildRun]
    longest: Optional[BuildRun]
    most_common_error: Optional[str]
    error_counts: dict[str, int]
    builds_by_date: dict[str, int]
    cost_by_date: dict[str, float]
    date_range_start: Optional[str]
    date_range_end: Optional[str]
