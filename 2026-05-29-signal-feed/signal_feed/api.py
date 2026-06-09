"""FastAPI application — REST API + WebSocket for Signal Feed."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import asyncio

from fastapi import FastAPI, HTTPException, Query, Depends, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from . import settings
from .database import (
    get_engine, get_session_factory, init_db,
    Signal, ApiKey,
)
from .collectors import collect_all
from .stripe_payments import router as stripe_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine, session_factory
    engine = get_engine(settings.DATABASE_URL)
    session_factory = get_session_factory(engine)
    await init_db(engine)

    # Seed a default API key
    async with session_factory() as session:
        existing = await session.execute(select(ApiKey).where(ApiKey.key == "sf-demo-key-2026"))
        if not existing.scalar_one_or_none():
            session.add(ApiKey(key="sf-demo-key-2026", tier="free", name="Default Demo Key"))
            await session.commit()

    yield


app = FastAPI(
    title="Signal Feed API",
    version="0.1.0",
    description="AI-powered market signal aggregator — news, social, on-chain",
    lifespan=lifespan,
)

app.include_router(stripe_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Startup ---
engine = None
session_factory = None
_latest_signals_cache: list[dict] = []
_last_fetch: datetime | None = None
async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    # Demo key bypass (no DB check needed)
    if x_api_key == "sf-demo-key-2026":
        return "free"

    if session_factory:
        async with session_factory() as session:
            result = await session.execute(
                select(ApiKey).where(ApiKey.key == x_api_key, ApiKey.is_active == 1)
            )
            key = result.scalar_one_or_none()
            if not key:
                raise HTTPException(status_code=401, detail="Invalid API key")
            key.requests_total += 1
            await session.commit()
            return key.tier

    return "free"


# --- REST Endpoints ---
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "last_fetch": _last_fetch.isoformat() if _last_fetch else None,
        "cached_signals": len(_latest_signals_cache),
    }


@app.get("/api/v1/signals")
async def get_signals(
    category: str = Query(None, description="Filter: crypto, stocks, general"),
    source: str = Query(None, description="Filter by source"),
    sentiment: str = Query(None, description="Filter: bullish, bearish, neutral"),
    min_score: float = Query(None, ge=-1.0, le=1.0, description="Min signal score"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tier: str = Depends(verify_api_key),
):
    """Get latest market signals, filterable and paginated."""
    signals = _latest_signals_cache

    if category:
        signals = [s for s in signals if s.get("category") == category]
    if source:
        signals = [s for s in signals if source.lower() in s.get("source", "").lower()]
    if sentiment:
        signals = [s for s in signals if s.get("sentiment_label") == sentiment]
    if min_score is not None:
        signals = [s for s in signals if abs(s.get("signal_score", 0)) >= min_score]

    total = len(signals)
    signals = signals[offset:offset + limit]

    return {
        "data": signals,
        "meta": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "tier": tier,
        },
    }


@app.get("/api/v1/signals/top")
async def get_top_signals(
    direction: str = Query("bullish", pattern="^(bullish|bearish)$"),
    limit: int = Query(10, ge=1, le=50),
    tier: str = Depends(verify_api_key),
):
    """Get top bullish or bearish signals by absolute score."""
    if direction == "bullish":
        sorted_signals = sorted(
            [s for s in _latest_signals_cache if s.get("signal_score", 0) > 0],
            key=lambda x: x.get("signal_score", 0),
            reverse=True,
        )
    else:
        sorted_signals = sorted(
            [s for s in _latest_signals_cache if s.get("signal_score", 0) < 0],
            key=lambda x: x.get("signal_score", 0),
        )

    return {"data": sorted_signals[:limit], "direction": direction, "tier": tier}


@app.get("/api/v1/sentiment/overview")
async def sentiment_overview(tier: str = Depends(verify_api_key)):
    """Get aggregate sentiment breakdown across all cached signals."""
    if not _latest_signals_cache:
        return {"overall": "neutral", "breakdown": {}, "total": 0}

    total = len(_latest_signals_cache)
    by_source: dict[str, dict] = defaultdict(lambda: {"total": 0, "bullish": 0, "bearish": 0, "neutral": 0, "avg_score": 0.0})
    by_cat: dict[str, dict] = defaultdict(lambda: {"total": 0, "bullish": 0, "bearish": 0, "neutral": 0, "avg_score": 0.0})

    for s in _latest_signals_cache:
        src = s.get("source", "unknown")
        cat = s.get("category", "general")
        label = s.get("sentiment_label", "neutral")
        score = s.get("signal_score", 0)

        for bucket in (by_source[src], by_cat[cat]):
            bucket["total"] += 1
            bucket[label] = bucket.get(label, 0) + 1
            bucket["avg_score"] += score

    for bucket in list(by_source.values()) + list(by_cat.values()):
        if bucket["total"] > 0:
            bucket["avg_score"] = round(bucket["avg_score"] / bucket["total"], 3)

    avg = sum(s.get("signal_score", 0) for s in _latest_signals_cache) / total
    overall = "bullish" if avg > 0.15 else "bearish" if avg < -0.15 else "neutral"

    return {
        "overall": overall,
        "average_score": round(avg, 3),
        "total_signals": total,
        "by_source": dict(by_source),
        "by_category": dict(by_cat),
        "tier": tier,
    }


@app.post("/api/v1/collect/trigger")
async def trigger_collection(tier: str = Depends(verify_api_key)):
    """Manually trigger a fresh signal collection run."""
    global _latest_signals_cache, _last_fetch

    raw_signals = await collect_all()
    _latest_signals_cache = raw_signals
    _last_fetch = datetime.now(timezone.utc)

    # Persist to DB if available
    if session_factory and engine:
        try:
            async with session_factory() as session:
                for sig_data in raw_signals:
                    signal_obj = Signal(
                        source=sig_data["source"],
                        category=sig_data["category"],
                        title=sig_data["title"],
                        url=sig_data.get("url"),
                        summary=sig_data.get("summary"),
                        signal_score=sig_data.get("signal_score", 0),
                        sentiment_label=sig_data.get("sentiment_label", "neutral"),
                        raw_score=sig_data.get("raw_score", 0),
                        metadata_json=sig_data.get("metadata_json"),
                    )
                    session.add(signal_obj)
                await session.commit()
        except Exception as e:
            pass  # Cache is already updated, DB failure is non-fatal

    return {
        "collected": len(raw_signals),
        "timestamp": _last_fetch.isoformat(),
        "tier": tier,
    }


# --- WebSocket ---
@app.websocket("/ws/v1/live")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming live signals (Pro tier)."""
    await websocket.accept()
    try:
        # Send current snapshot
        await websocket.send_json({
            "type": "snapshot",
            "data": _latest_signals_cache[:20],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Keep alive, push updates every 30 seconds
        import asyncio
        while True:
            await asyncio.sleep(30)
            if _latest_signals_cache:
                await websocket.send_json({
                    "type": "heartbeat",
                    "cached_signals": len(_latest_signals_cache),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    except WebSocketDisconnect:
        pass


# --- CLI entrypoint ---
def main():
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)


if __name__ == "__main__":
    main()
