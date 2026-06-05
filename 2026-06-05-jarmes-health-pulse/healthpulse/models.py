"""Pydantic models for health pulse data structures."""

from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    UNKNOWN = "unknown"


class LogEntry(BaseModel):
    """A single parsed log line."""
    timestamp: Optional[dt.datetime] = None
    level: str = "INFO"
    source: str = ""  # e.g., "apscheduler.executors.default"
    message: str = ""
    raw: str = ""
    job_name: Optional[str] = None
    is_error: bool = False
    is_success: bool = False
    traceback: Optional[str] = None


class JobHealth(BaseModel):
    """Health status for a single cron job."""
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    total_runs: int = 0
    total_errors: int = 0
    total_successes: int = 0
    error_rate: float = 0.0
    last_error: Optional[str] = None
    last_error_time: Optional[dt.datetime] = None
    last_success_time: Optional[dt.datetime] = None
    first_seen: Optional[dt.datetime] = None
    top_errors: list[dict] = Field(default_factory=list)
    suggestion: Optional[str] = None


class ErrorPattern(BaseModel):
    """A recurring error pattern."""
    pattern: str
    count: int = 0
    first_seen: Optional[dt.datetime] = None
    last_seen: Optional[dt.datetime] = None
    sample_message: str = ""
    job_name: Optional[str] = None
    suggestion: Optional[str] = None


class SystemHealth(BaseModel):
    """Overall system health snapshot."""
    generated_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)
    log_sources: list[str] = Field(default_factory=list)
    total_lines_parsed: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    jobs: list[JobHealth] = Field(default_factory=list)
    top_error_patterns: list[ErrorPattern] = Field(default_factory=list)
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    uptime_estimate: Optional[str] = None
