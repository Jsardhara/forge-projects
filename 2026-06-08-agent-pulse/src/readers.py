"""JSONL file readers for AgentPulse."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

# Bus directory default
BUS_DIR_DEFAULT = Path(os.environ.get(
    "AGENTPULSE_BUS_DIR",
    str(Path.home() / r"AppData\Local\hermes\state\bus")
))


def _state_dir() -> Path:
    """Resolve state directory from env var each call."""
    raw = os.environ.get("AGENTPULSE_STATE_DIR")
    if raw:
        return Path(raw)
    return Path(r"C:\Users\jyot2\jarvis\state")


def _bus_dir() -> Path:
    """Resolve bus directory from env var each call."""
    raw = os.environ.get("AGENTPULSE_BUS_DIR")
    if raw:
        return Path(raw)
    return BUS_DIR_DEFAULT


def read_jsonl(
    filename: str,
    state_dir: Optional[Path] = None,
    last_n: int = 100,
) -> list[dict[str, Any]]:
    """Read a JSONL file and return the last N parsed lines.

    Skips lines that fail to parse. Returns empty list if file doesn't exist.
    """
    d = state_dir or _state_dir()
    path = d / filename
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # skip corrupt lines
    except (OSError, PermissionError):
        return []

    return rows[-last_n:]


def read_agent_log(last_n: int = 50) -> list[dict[str, Any]]:
    """Read recent agent_log entries."""
    return read_jsonl("agent_log.jsonl", last_n=last_n)


def read_builds(last_n: int = 20) -> list[dict[str, Any]]:
    """Read recent build records."""
    return read_jsonl("daily_projects.jsonl", last_n=last_n)


def read_health(last_n: int = 10) -> list[dict[str, Any]]:
    """Read recent sentinel health checks."""
    return read_jsonl("sentinel_health.jsonl", last_n=last_n)


def read_costs(last_n: int = 100) -> list[dict[str, Any]]:
    """Read recent cost log entries."""
    return read_jsonl("cost_log.jsonl", last_n=last_n)


def read_bus_messages(last_n: int = 20) -> list[dict[str, Any]]:
    """Read recent bus messages from the inbox directory."""
    inbox_dir = _bus_dir() / "inbox"
    if not inbox_dir.exists():
        return []

    messages: list[dict[str, Any]] = []
    try:
        for f in sorted(inbox_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.suffix == ".json":
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    messages.append(data)
                except (json.JSONDecodeError, OSError):
                    continue
                if len(messages) >= last_n:
                    break
    except (OSError, PermissionError):
        return []

    return messages


def compute_stats(
    builds: list[dict[str, Any]],
    agent_events: list[dict[str, Any]],
    costs: list[dict[str, Any]],
    health: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute aggregated system statistics."""
    total_builds = len(builds)
    successful = sum(1 for b in builds if b.get("status") == "success")
    failed = sum(1 for b in builds if b.get("status") in ("failed", "error"))

    total_cost = 0.0
    for c in costs:
        cost = c.get("cost_usd")
        if cost is not None:
            try:
                total_cost += float(cost)
            except (TypeError, ValueError):
                pass

    agents_set: set[str] = set()
    for evt in agent_events:
        a = evt.get("agent")
        if a:
            agents_set.add(a)

    last_build_date = None
    last_build_status = None
    if builds:
        last = builds[-1]
        last_build_date = last.get("date") or last.get("ts", "")[:10]
        last_build_status = last.get("status")

    sentinel_jobs = 0
    if health:
        latest = health[-1]
        sentinel_jobs = latest.get("job_count", 0)

    return {
        "total_builds": total_builds,
        "successful_builds": successful,
        "failed_builds": failed,
        "total_cost_usd": round(total_cost, 4),
        "total_agent_events": len(agent_events),
        "active_agents": sorted(agents_set),
        "sentinel_jobs": sentinel_jobs,
        "last_build_date": last_build_date,
        "last_build_status": last_build_status,
    }
