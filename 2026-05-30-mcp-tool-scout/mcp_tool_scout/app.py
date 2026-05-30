"""FastAPI application for MCP Tool Scout."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Optional

import structlog
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mcp_tool_scout import (
    GitHubCollector,
    ScoreBreakdown,
    ScoringEngine,
    SearchResult,
    ServerStore,
    McpServer,
    seed_store,
)

logger = structlog.get_logger(__name__)

# ── Global State ────────────────────────────────────────────────────────────────

store = ServerStore()
engine = ScoringEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Seed data on startup; optionally refresh from GitHub if token is set."""
    token = os.environ.get("GITHUB_TOKEN", "")
    github_refreshed = False

    if token:
        try:
            collector = GitHubCollector(token=token)
            count = 0
            async for server in collector.collect():
                store.upsert(server)
                count += 1
            logger.info("github_refresh_complete", count=count)
            github_refreshed = True
        except Exception as exc:
            logger.warning("github_refresh_failed", error=str(exc))

    if not github_refreshed:
        seed_store(store)
        logger.info("seed_data_loaded", count=store.count)

    yield


app = FastAPI(
    title="MCP Tool Scout",
    version="0.1.0",
    description="Discover, score, and search MCP servers for AI agents",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API Endpoints ───────────────────────────────────────────────────────────────


@app.get("/", response_class=JSONResponse)
async def root():
    return {
        "service": "MCP Tool Scout",
        "version": "0.1.0",
        "endpoints": {
            "GET /servers": "List/search MCP servers",
            "GET /servers/{id}": "Get server details",
            "GET /servers/{id}/score": "Get detailed scoring breakdown",
            "POST /collect": "Trigger GitHub collection (requires GITHUB_TOKEN)",
            "GET /health": "Health check",
        },
        "total_servers": store.count,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "servers_indexed": store.count}


@app.get("/servers", response_model=SearchResult)
async def list_servers(
    q: str = Query("", description="Search query"),
    min_score: float = Query(0.0, ge=0, le=100),
    sort: str = Query("score", regex="^(score|stars|forks)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    return store.search(
        query=q,
        min_score=min_score,
        sort=sort,
        page=page,
        per_page=per_page,
    )


@app.get("/servers/top", response_model=SearchResult)
async def top_servers(limit: int = Query(10, ge=1, le=50)):
    return store.search(sort="score", limit=limit)


@app.get("/servers/{server_id}", response_model=McpServer)
async def get_server(server_id: str):
    server = store.get(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@app.get("/servers/{server_id}/score", response_model=ScoreBreakdown)
async def get_score(server_id: str):
    server = store.get(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return engine.breakdown(server)


@app.post("/collect")
async def trigger_collection():
    """Trigger a fresh GitHub collection. Requires GITHUB_TOKEN env var."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise HTTPException(
            status_code=400,
            detail="GITHUB_TOKEN environment variable not set",
        )

    collector = GitHubCollector(token=token)
    count = 0
    async for server in collector.collect():
        store.upsert(server)
        count += 1

    return {"collected": count, "total_servers": store.count}
