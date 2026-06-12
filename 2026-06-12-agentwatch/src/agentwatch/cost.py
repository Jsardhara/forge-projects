"""Cost tracking and budget enforcement for AI agents."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from agentwatch.db import (
    get_db,
    get_total_spend,
    set_budget,
    get_budget,
    record_spend,
    create_alert,
    get_spend,
)


@dataclass
class SpendReport:
    agent_id: str
    daily_spend: float
    monthly_spend: float
    daily_limit: float
    monthly_limit: float
    daily_pct: float
    monthly_pct: float
    budget_exceeded: bool
    alert_triggered: bool


def check_budget(conn, agent_id: str) -> SpendReport:
    """Check an agent's spending against its budget."""
    now = time.time()
    day_ago = now - 86400
    month_ago = now - 30 * 86400

    daily_spend = get_total_spend(conn, agent_id, since=day_ago)
    monthly_spend = get_total_spend(conn, agent_id, since=month_ago)

    budget = get_budget(conn, agent_id)
    if not budget:
        daily_limit = 5.0
        monthly_limit = 100.0
        threshold = 80.0
    else:
        daily_limit = budget["daily_limit_usd"]
        monthly_limit = budget["monthly_limit_usd"]
        threshold = budget["alert_threshold_pct"]

    daily_pct = (daily_spend / daily_limit * 100) if daily_limit > 0 else 0.0
    monthly_pct = (monthly_spend / monthly_limit * 100) if monthly_limit > 0 else 0.0

    budget_exceeded = daily_spend >= daily_limit or monthly_spend >= monthly_limit
    alert_triggered = daily_pct >= threshold or monthly_pct >= threshold

    if budget_exceeded:
        create_alert(
            conn,
            alert_type="budget_exceeded",
            agent_id=agent_id,
            message=f"Budget exceeded for agent {agent_id}: daily=${daily_spend:.2f}/${daily_limit:.2f}, monthly=${monthly_spend:.2f}/${monthly_limit:.2f}",
            severity="alert",
        )
    elif alert_triggered:
        create_alert(
            conn,
            alert_type="budget_warning",
            agent_id=agent_id,
            message=f"Budget warning for agent {agent_id}: daily={daily_pct:.0f}%, monthly={monthly_pct:.0f}%",
            severity="warn",
        )

    return SpendReport(
        agent_id=agent_id,
        daily_spend=daily_spend,
        monthly_spend=monthly_spend,
        daily_limit=daily_limit,
        monthly_limit=monthly_limit,
        daily_pct=round(daily_pct, 1),
        monthly_pct=round(monthly_pct, 1),
        budget_exceeded=budget_exceeded,
        alert_triggered=alert_triggered,
    )


def estimate_cost(tokens_in: int, tokens_out: int, model: str = "gpt-4o") -> float:
    """Estimate USD cost for a given token usage and model."""
    # Per-token pricing (USD per 1M tokens)
    pricing = {
        "gpt-4o": {"in": 2.50, "out": 10.00},
        "gpt-4o-mini": {"in": 0.15, "out": 0.60},
        "claude-sonnet-4": {"in": 3.00, "out": 15.00},
        "claude-haiku-4": {"in": 0.25, "out": 1.25},
        "gemini-2.5-pro": {"in": 1.25, "out": 10.00},
        "gemini-2.5-flash": {"in": 0.15, "out": 0.60},
    }
    p = pricing.get(model, pricing["gpt-4o"])
    return (tokens_in * p["in"] + tokens_out * p["out"]) / 1_000_000
