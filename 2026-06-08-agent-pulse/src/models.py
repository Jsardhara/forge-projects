"""Pydantic models for AgentPulse data."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentEvent(BaseModel):
    """Single agent action from agent_log.jsonl."""
    ts: Optional[str] = None
    request_id: Optional[str] = None
    agent: Optional[str] = None
    action: Optional[str] = None
    status: Optional[str] = None
    duration_ms: Optional[int] = None
    confidence: Optional[float] = None
    needs_confirm: Optional[bool] = None
    summary: Optional[str] = None
    error: Optional[str] = None


class BuildRecord(BaseModel):
    """Single forge build from daily_projects.jsonl."""
    ts: Optional[str] = None
    date: Optional[str] = None
    status: Optional[str] = None
    slug: Optional[str] = None
    title: Optional[str] = None
    folder: Optional[str] = None
    repo_url: Optional[str] = None
    cost_usd: Optional[float] = None
    duration_sec: Optional[float] = None
    error: Optional[str] = None


class HealthRecord(BaseModel):
    """Single sentinel health check from sentinel_health.jsonl."""
    ts: Optional[str] = None
    job_count: Optional[int] = None
    jobs: Optional[dict[str, str]] = None


class CostRecord(BaseModel):
    """Single cost entry from cost_log.jsonl."""
    ts: Optional[str] = None
    agent: Optional[str] = None
    model: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost_usd: Optional[float] = None


class BusMessage(BaseModel):
    """Single bus message."""
    id: Optional[str] = None
    topic: Optional[str] = None
    from_agent: Optional[str] = None
    to_agent: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    ts: Optional[str] = None
    read: Optional[bool] = None


class SystemStats(BaseModel):
    """Aggregated system statistics."""
    total_builds: int = 0
    successful_builds: int = 0
    failed_builds: int = 0
    total_cost_usd: float = 0.0
    total_agent_events: int = 0
    active_agents: list[str] = Field(default_factory=list)
    sentinel_jobs: int = 0
    last_build_date: Optional[str] = None
    last_build_status: Optional[str] = None
