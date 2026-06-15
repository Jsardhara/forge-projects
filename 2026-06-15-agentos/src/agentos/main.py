"""AgentOS — AI Agent Orchestration & Governance Platform.

Main FastAPI application with API endpoints and dashboard.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from agentos.audit import AuditLogger
from agentos.costs import CostTracker
from agentos.models import Agent, Policy, init_db
from agentos.policy import PolicyEngine


# Pydantic request/response models
class AgentCreate(BaseModel):
    id: str
    name: str
    agent_type: str = "custom"
    description: str = ""
    max_spend_per_run: float = 1.0
    max_daily_spend: float = 10.0


class PolicyCreate(BaseModel):
    id: str
    name: str
    description: str = ""
    scope: str = "global"
    scope_id: Optional[str] = None
    max_spend_per_run: Optional[float] = None
    max_daily_spend: Optional[float] = None
    blocked_tools: str = ""
    require_approval_for: str = ""


class PolicyCheckRequest(BaseModel):
    agent_id: str
    estimated_cost: float = 0.0
    tools_requested: list[str] = []
    action_type: str = "run"


class AuditEntryCreate(BaseModel):
    agent_id: str
    action: str
    input_summary: str = ""
    output_summary: str = ""
    cost: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    policy_decision: str = "allow"
    policy_reason: str = ""


class CostEntryCreate(BaseModel):
    agent_id: str
    amount: float
    tokens_in: int = 0
    tokens_out: int = 0
    description: str = ""


# Lifespan for startup/shutdown
@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AgentOS",
    description="AI Agent Orchestration & Governance Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Service instances
policy_engine = PolicyEngine()
cost_tracker = CostTracker()
audit_logger = AuditLogger()


# ─── Dashboard ───────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard."""
    summary = cost_tracker.get_summary()
    recent_logs = audit_logger.get_logs(limit=10)

    agents_html = ""
    from agentos.models import get_session
    session = get_session()
    try:
        agents = session.query(Agent).filter(Agent.is_active == True).all()
        for agent in agents:
            agent_cost = cost_tracker.get_agent_cost(agent.id)
            agents_html += f"""
            <tr>
                <td><strong>{agent.name}</strong></td>
                <td><span class="badge">{agent.agent_type}</span></td>
                <td>${agent_cost['total_cost']:.4f}</td>
                <td>${agent_cost['daily_cost']:.4f}</td>
                <td>{agent_cost['tokens_in'] + agent_cost['tokens_out']:,}</td>
                <td><span class="status-ok">● Active</span></td>
            </tr>"""
    finally:
        session.close()

    logs_html = ""
    for log_entry in recent_logs:
        decision_class = {
            "allow": "status-ok",
            "flag": "status-warn",
            "block": "status-err",
        }.get(log_entry.policy_decision, "")
        logs_html += f"""
        <tr>
            <td>{log_entry.created_at.strftime('%H:%M:%S')}</td>
            <td>{log_entry.agent_id}</td>
            <td>{log_entry.action}</td>
            <td>${log_entry.cost:.4f}</td>
            <td><span class="{decision_class}">{log_entry.policy_decision}</span></td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgentOS — Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #0a0a0b; --surface: #111113; --border: #27272a;
  --text: #fafafa; --muted: #a1a1aa; --accent: #6366f1;
  --ok: #22c55e; --warn: #f59e0b; --err: #ef4444;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Inter', -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border); }}
header h1 {{ font-size: 1.5rem; font-weight: 700; }}
header h1 span {{ color: var(--accent); }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; padding: 1.5rem; }}
.card h3 {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-bottom: 0.5rem; }}
.card .value {{ font-size: 1.75rem; font-weight: 700; }}
.card .sub {{ font-size: 0.8rem; color: var(--muted); margin-top: 0.25rem; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ text-align: left; padding: 0.75rem; border-bottom: 1px solid var(--border); }}
th {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); }}
.badge {{ background: var(--accent); color: white; padding: 0.15rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem; }}
.status-ok {{ color: var(--ok); }}
.status-warn {{ color: var(--warn); }}
.status-err {{ color: var(--err); }}
.section {{ margin-bottom: 2rem; }}
.section h2 {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>Agent<span>OS</span> — Dashboard</h1>
    <span style="color: var(--muted); font-size: 0.85rem;">AI Agent Orchestration & Governance</span>
  </header>

  <div class="grid">
    <div class="card">
      <h3>Total Cost</h3>
      <div class="value">${summary.total_cost:.4f}</div>
      <div class="sub">All time</div>
    </div>
    <div class="card">
      <h3>Daily Cost</h3>
      <div class="value">${summary.daily_cost:.4f}</div>
      <div class="sub">Today</div>
    </div>
    <div class="card">
      <h3>Active Agents</h3>
      <div class="value">{summary.agent_count}</div>
      <div class="sub">Registered</div>
    </div>
    <div class="card">
      <h3>Total Tokens</h3>
      <div class="value">{(summary.total_tokens_in + summary.total_tokens_out):,}</div>
      <div class="sub">In: {summary.total_tokens_in:,} / Out: {summary.total_tokens_out:,}</div>
    </div>
  </div>

  <div class="section">
    <h2>Agents</h2>
    <div class="card" style="overflow-x: auto;">
      <table>
        <thead><tr><th>Name</th><th>Type</th><th>Total Cost</th><th>Daily Cost</th><th>Tokens</th><th>Status</th></tr></thead>
        <tbody>{agents_html if agents_html else '<tr><td colspan="6" style="text-align:center;color:var(--muted);">No agents registered</td></tr>'}</tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <h2>Recent Activity</h2>
    <div class="card" style="overflow-x: auto;">
      <table>
        <thead><tr><th>Time</th><th>Agent</th><th>Action</th><th>Cost</th><th>Decision</th></tr></thead>
        <tbody>{logs_html if logs_html else '<tr><td colspan="5" style="text-align:center;color:var(--muted);">No activity recorded</td></tr>'}</tbody>
      </table>
    </div>
  </div>
</div>
</body>
</html>"""


# ─── Health Check ─────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "agentos", "version": "0.1.0"}


# ─── Agent Endpoints ──────────────────────────────────────────

@app.get("/api/agents")
async def list_agents():
    from agentos.models import get_session
    session = get_session()
    try:
        agents = session.query(Agent).all()
        return [
            {
                "id": a.id,
                "name": a.name,
                "agent_type": a.agent_type,
                "description": a.description,
                "max_spend_per_run": a.max_spend_per_run,
                "max_daily_spend": a.max_daily_spend,
                "is_active": a.is_active,
                "created_at": a.created_at.isoformat(),
            }
            for a in agents
        ]
    finally:
        session.close()


@app.post("/api/agents")
async def create_agent(body: AgentCreate):
    from agentos.models import get_session
    session = get_session()
    try:
        existing = session.query(Agent).filter(Agent.id == body.id).first()
        if existing:
            raise HTTPException(status_code=409, detail="Agent already exists")
        agent = Agent(
            id=body.id,
            name=body.name,
            agent_type=body.agent_type,
            description=body.description,
            max_spend_per_run=body.max_spend_per_run,
            max_daily_spend=body.max_daily_spend,
        )
        session.add(agent)
        session.commit()
        return {"id": agent.id, "name": agent.name, "status": "created"}
    finally:
        session.close()


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    from agentos.models import get_session
    session = get_session()
    try:
        agent = session.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        cost = cost_tracker.get_agent_cost(agent_id)
        return {
            "id": agent.id,
            "name": agent.name,
            "agent_type": agent.agent_type,
            "description": agent.description,
            "max_spend_per_run": agent.max_spend_per_run,
            "max_daily_spend": agent.max_daily_spend,
            "is_active": agent.is_active,
            "cost": cost,
        }
    finally:
        session.close()


# ─── Policy Endpoints ─────────────────────────────────────────

@app.get("/api/policies")
async def list_policies():
    from agentos.models import get_session
    session = get_session()
    try:
        policies = session.query(Policy).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "scope": p.scope,
                "scope_id": p.scope_id,
                "max_spend_per_run": p.max_spend_per_run,
                "max_daily_spend": p.max_daily_spend,
                "blocked_tools": p.blocked_tools,
                "require_approval_for": p.require_approval_for,
                "is_active": p.is_active,
            }
            for p in policies
        ]
    finally:
        session.close()


@app.post("/api/policies")
async def create_policy(body: PolicyCreate):
    from agentos.models import get_session
    session = get_session()
    try:
        existing = session.query(Policy).filter(Policy.id == body.id).first()
        if existing:
            raise HTTPException(status_code=409, detail="Policy already exists")
        policy = Policy(
            id=body.id,
            name=body.name,
            description=body.description,
            scope=body.scope,
            scope_id=body.scope_id,
            max_spend_per_run=body.max_spend_per_run,
            max_daily_spend=body.max_daily_spend,
            blocked_tools=body.blocked_tools,
            require_approval_for=body.require_approval_for,
        )
        session.add(policy)
        session.commit()
        return {"id": policy.id, "name": policy.name, "status": "created"}
    finally:
        session.close()


@app.post("/api/policies/check")
async def check_policy(body: PolicyCheckRequest):
    result = policy_engine.check_request(
        agent_id=body.agent_id,
        estimated_cost=body.estimated_cost,
        tools_requested=body.tools_requested,
        action_type=body.action_type,
    )
    return {
        "decision": result.decision,
        "reasons": result.reasons,
        "is_allowed": result.is_allowed,
        "is_flagged": result.is_flagged,
        "max_spend_per_run": result.max_spend_per_run,
        "max_daily_spend": result.max_daily_spend,
        "blocked_tools": result.blocked_tools,
        "requires_approval_for": result.requires_approval_for,
    }


# ─── Audit Endpoints ──────────────────────────────────────────

@app.get("/api/audit")
async def list_audit_logs(
    agent_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    logs = audit_logger.get_logs(agent_id=agent_id, limit=limit, offset=offset)
    total = audit_logger.get_log_count(agent_id=agent_id)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "entries": [
            {
                "id": log_entry.id,
                "agent_id": log_entry.agent_id,
                "action": log_entry.action,
                "input_summary": log_entry.input_summary,
                "output_summary": log_entry.output_summary,
                "cost": log_entry.cost,
                "tokens_in": log_entry.tokens_in,
                "tokens_out": log_entry.tokens_out,
                "policy_decision": log_entry.policy_decision,
                "policy_reason": log_entry.policy_reason,
                "created_at": log_entry.created_at.isoformat(),
            }
            for log_entry in logs
        ],
    }


@app.post("/api/audit")
async def create_audit_entry(body: AuditEntryCreate):
    entry = audit_logger.log(
        agent_id=body.agent_id,
        action=body.action,
        input_summary=body.input_summary,
        output_summary=body.output_summary,
        cost=body.cost,
        tokens_in=body.tokens_in,
        tokens_out=body.tokens_out,
        policy_decision=body.policy_decision,
        policy_reason=body.policy_reason,
    )
    return {"id": entry.id, "status": "recorded"}


# ─── Cost Endpoints ───────────────────────────────────────────

@app.get("/api/costs")
async def get_cost_summary():
    summary = cost_tracker.get_summary()
    return {
        "total_cost": summary.total_cost,
        "daily_cost": summary.daily_cost,
        "total_tokens_in": summary.total_tokens_in,
        "total_tokens_out": summary.total_tokens_out,
        "agent_count": summary.agent_count,
        "top_spenders": summary.top_spenders,
    }


@app.get("/api/costs/{agent_id}")
async def get_agent_cost(agent_id: str):
    from agentos.models import get_session
    session = get_session()
    try:
        agent = session.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return cost_tracker.get_agent_cost(agent_id)
    finally:
        session.close()


@app.post("/api/costs")
async def record_cost(body: CostEntryCreate):
    from agentos.models import get_session
    session = get_session()
    try:
        agent = session.query(Agent).filter(Agent.id == body.agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        record = cost_tracker.record_cost(
            agent_id=body.agent_id,
            amount=body.amount,
            tokens_in=body.tokens_in,
            tokens_out=body.tokens_out,
            description=body.description,
        )
        return {"id": record.id, "status": "recorded"}
    finally:
        session.close()
