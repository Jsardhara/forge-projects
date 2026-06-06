"""FastAPI REST API for AI Failbook."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from ai_failbook.models import (
    Category,
    FailureMode,
    FailureModeCreate,
    FailureModeUpdate,
    SearchQuery,
    SearchResult,
    Severity,
    Stats,
)
from ai_failbook.store import Store

# Default DB path
DEFAULT_DB = Path(__file__).parent.parent / "failbook.db"


def get_store(db_path: Optional[str] = None) -> Store:
    path = db_path or str(DEFAULT_DB)
    return Store(path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Seed sample data on first startup."""
    store = get_store()
    existing = store.search(SearchQuery(limit=1))
    if existing.total == 0:
        store.seed_sample_data()
    yield
    store.close()


app = FastAPI(
    title="AI Failbook",
    description="Structured AI failure mode database — catalog, search, and learn from AI fuckups",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "name": "AI Failbook",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "search": "GET /failures",
            "get": "GET /failures/{vid}",
            "create": "POST /failures",
            "update": "PATCH /failures/{vid}",
            "delete": "DELETE /failures/{vid}",
            "upvote": "POST /failures/{vid}/upvote",
            "stats": "GET /stats",
            "categories": "GET /categories",
            "severities": "GET /severities",
        },
    }


@app.get("/failures", response_model=SearchResult)
async def search_failures(
    q: Optional[str] = Query(None, description="Full-text search"),
    category: Optional[Category] = Query(None),
    severity: Optional[Severity] = Query(None),
    model: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    verified_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    query = SearchQuery(
        q=q, category=category, severity=severity,
        model=model, tag=tag, verified_only=verified_only,
        limit=limit, offset=offset,
    )
    store = get_store()
    return store.search(query)


@app.get("/failures/{vid}", response_model=FailureMode)
async def get_failure(vid: str):
    store = get_store()
    fm = store.get(vid)
    if fm is None:
        raise HTTPException(status_code=404, detail=f"Failure mode {vid} not found")
    return fm


@app.post("/failures", response_model=FailureMode, status_code=201)
async def create_failure(data: FailureModeCreate):
    store = get_store()
    return store.create(data)


@app.patch("/failures/{vid}", response_model=FailureMode)
async def update_failure(vid: str, data: FailureModeUpdate):
    store = get_store()
    fm = store.update(vid, data)
    if fm is None:
        raise HTTPException(status_code=404, detail=f"Failure mode {vid} not found")
    return fm


@app.delete("/failures/{vid}")
async def delete_failure(vid: str):
    store = get_store()
    deleted = store.delete(vid)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Failure mode {vid} not found")
    return {"deleted": True, "vid": vid}


@app.post("/failures/{vid}/upvote", response_model=FailureMode)
async def upvote_failure(vid: str):
    store = get_store()
    fm = store.upvote(vid)
    if fm is None:
        raise HTTPException(status_code=404, detail=f"Failure mode {vid} not found")
    return fm


@app.get("/stats", response_model=Stats)
async def get_stats():
    store = get_store()
    return store.stats()


@app.get("/categories")
async def list_categories():
    return [{"value": c.value, "label": c.value.replace("_", " ").title()} for c in Category]


@app.get("/severities")
async def list_severities():
    return [{"value": s.value, "label": s.value.upper()} for s in Severity]
