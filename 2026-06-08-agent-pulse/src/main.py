"""FastAPI application for AgentPulse dashboard."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .readers import (
    read_agent_log,
    read_builds,
    read_bus_messages,
    read_costs,
    read_health,
    compute_stats,
)

# Determine static directory
STATIC_DIR = Path(__file__).parent.parent / "static"

app = FastAPI(
    title="AgentPulse",
    version="0.1.0",
    description="Multi-Agent Activity Dashboard for Jarmes",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/agents")
async def get_agents(limit: int = Query(50, ge=1, le=500)):
    """Get recent agent activity events."""
    return read_agent_log(last_n=limit)


@app.get("/api/builds")
async def get_builds(limit: int = Query(20, ge=1, le=100)):
    """Get recent forge build records."""
    return read_builds(last_n=limit)


@app.get("/api/health")
async def get_health(limit: int = Query(10, ge=1, le=100)):
    """Get recent sentinel health checks."""
    return read_health(last_n=limit)


@app.get("/api/costs")
async def get_costs(limit: int = Query(100, ge=1, le=1000)):
    """Get recent cost log entries."""
    return read_costs(last_n=limit)


@app.get("/api/bus")
async def get_bus(limit: int = Query(20, ge=1, le=100)):
    """Get recent bus messages."""
    return read_bus_messages(last_n=limit)


@app.get("/api/stats")
async def get_stats():
    """Get aggregated system statistics."""
    builds = read_builds(last_n=100)
    agents = read_agent_log(last_n=500)
    costs = read_costs(last_n=1000)
    health = read_health(last_n=1)
    return compute_stats(builds, agents, costs, health)


@app.get("/api/all")
async def get_all():
    """Get all dashboard data in one call."""
    builds = read_builds(last_n=20)
    agents = read_agent_log(last_n=50)
    costs = read_costs(last_n=100)
    health = read_health(last_n=5)
    bus = read_bus_messages(last_n=10)
    stats = compute_stats(builds, agents, costs, health)
    return {
        "stats": stats,
        "builds": builds,
        "agents": agents,
        "costs": costs,
        "health": health,
        "bus": bus,
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard HTML."""
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>AgentPulse</h1><p>Dashboard not found. Run from project directory.</p>")
