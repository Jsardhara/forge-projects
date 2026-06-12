"""FastAPI REST API for AgentWatch."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agentwatch.db import (
    get_db,
    register_agent,
    list_agents,
    get_agent,
    record_spend,
    get_spend,
    set_budget,
    get_budget,
    create_guardrail_probe,
    list_guardrail_probes,
    get_guardrail_probe,
    create_alert,
    list_alerts,
    acknowledge_alert,
)
from agentwatch.cost import check_budget, estimate_cost, SpendReport
from agentwatch.guardrail import run_probe, get_drift_trend, ProbeResult


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Could init connection pool here
    yield
    # Cleanup


app = FastAPI(
    title="AgentWatch",
    description="AI Agent Cost & Guardrail Monitoring",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Pydantic models ──

class AgentCreate(BaseModel):
    agent_id: str
    name: str
    provider: str = "openai"


class SpendRecord(BaseModel):
    agent_id: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


class BudgetSet(BaseModel):
    agent_id: str
    daily_limit_usd: float = 5.0
    monthly_limit_usd: float = 100.0
    alert_threshold_pct: float = 80.0


class ProbeCreate(BaseModel):
    probe_id: str
    name: str
    provider: str
    model: str
    prompt: str
    expected_keywords: list[str] = []
    interval_seconds: int = 3600


class CostEstimate(BaseModel):
    tokens_in: int
    tokens_out: int
    model: str = "gpt-4o"


# ── Agent endpoints ──

@app.get("/agents")
async def get_agents():
    """List all monitored agents."""
    conn = get_db()
    agents = list_agents(conn)
    return {"agents": agents}


@app.post("/agents")
async def create_agent(body: AgentCreate):
    """Register a new agent."""
    conn = get_db()
    agent = register_agent(conn, body.agent_id, body.name, body.provider)
    agent["budget"] = get_budget(conn, body.agent_id)
    return agent


@app.get("/agents/{agent_id}")
async def get_agent_detail(agent_id: str):
    """Get agent details with spend data."""
    conn = get_db()
    agent = get_agent(conn, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent["budget"] = get_budget(conn, agent_id)
    agent["spend_report"] = check_budget(conn, agent_id)
    return agent


@app.get("/agents/{agent_id}/spend")
async def get_agent_spend(agent_id: str, hours: int | None = None):
    """Get spending records for an agent."""
    conn = get_db()
    since = None
    if hours:
        import time
        since = time.time() - hours * 3600
    records = get_spend(conn, agent_id, since=since)
    return {"agent_id": agent_id, "records": records, "total": sum(r["cost_usd"] for r in records)}


@app.post("/agents/{agent_id}/spend")
async def record_agent_spend(agent_id: str, body: SpendRecord):
    """Record a spend event for an agent."""
    conn = get_db()
    record = record_spend(conn, agent_id, body.tokens_in, body.tokens_out, body.cost_usd)
    report = check_budget(conn, agent_id)
    return {"record": record, "budget_status": report}


@app.post("/agents/{agent_id}/budget")
async def set_agent_budget(agent_id: str, body: BudgetSet):
    """Set budget limits for an agent."""
    conn = get_db()
    budget = set_budget(conn, agent_id, body.daily_limit_usd, body.monthly_limit_usd, body.alert_threshold_pct)
    return budget


# ── Guardrail endpoints ──

@app.get("/guardrails")
async def get_guardrails():
    """List all guardrail probes."""
    conn = get_db()
    probes = list_guardrail_probes(conn)
    return {"probes": probes}


@app.post("/guardrails")
async def create_probe(body: ProbeCreate):
    """Create a new guardrail probe."""
    import json
    conn = get_db()
    probe = create_guardrail_probe(
        conn,
        body.probe_id,
        body.name,
        body.provider,
        body.model,
        body.prompt,
        expected_keywords=json.dumps(body.expected_keywords),
        interval_seconds=body.interval_seconds,
    )
    return probe


@app.post("/guardrails/{probe_id}/check")
async def run_guardrail_check(probe_id: str):
    """Run a guardrail probe check."""
    import json
    conn = get_db()
    result = run_probe(conn, probe_id)
    return {
        "probe_id": result.probe_id,
        "passed": result.passed,
        "drift_score": result.drift_score,
        "keywords_found": result.keywords_found,
        "keywords_missing": result.keywords_missing,
        "checked_at": result.checked_at,
    }


@app.get("/guardrails/{probe_id}/trend")
async def get_probe_trend(probe_id: str, window: int = 10):
    """Get drift trend for a probe."""
    conn = get_db()
    trend = get_drift_trend(conn, probe_id, window=window)
    return {"probe_id": probe_id, "trend": trend}


# ── Alert endpoints ──

@app.get("/alerts")
async def get_alerts(unread: bool = False, limit: int = 50):
    """List alerts."""
    conn = get_db()
    alerts = list_alerts(conn, unread_only=unread, limit=limit)
    return {"alerts": alerts}


@app.post("/alerts/{alert_id}/acknowledge")
async def ack_alert(alert_id: int):
    """Acknowledge an alert."""
    conn = get_db()
    ok = acknowledge_alert(conn, alert_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"acknowledged": True}


# ── Cost estimation ──

@app.post("/estimate")
async def estimate(body: CostEstimate):
    """Estimate cost for a token usage."""
    cost = estimate_cost(body.tokens_in, body.tokens_out, body.model)
    return {"model": body.model, "tokens_in": body.tokens_in, "tokens_out": body.tokens_out, "estimated_cost_usd": round(cost, 6)}


# ── Health ──

@app.get("/health")
async def health():
    return {"status": "ok", "service": "agentwatch"}
