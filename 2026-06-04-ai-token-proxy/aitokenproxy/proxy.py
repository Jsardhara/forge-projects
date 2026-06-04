"""FastAPI proxy server — intercepts LLM API calls and compresses tokens.

Usage:
    uvicorn aitokenproxy.proxy:app --port 9090

Then point your AI tool's API base URL to http://localhost:9090/openai or /anthropic.
"""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
import httpx

from .compressor import CompressionPipeline, count_tokens
from .tokens import PRICING, estimate_cost

app = FastAPI(title="AITokenProxy", version="0.1.0")

# In-memory stats store (swap for Redis in production)
stats_store: dict[str, list[dict]] = defaultdict(list)

# Upstream URLs
OPENAI_UPSTREAM = "https://api.openai.com"
ANTHROPIC_UPSTREAM = "https://api.anthropic.com"


def _get_upstream(path: str) -> str:
    if "anthropic" in path:
        return ANTHROPIC_UPSTREAM
    return OPENAI_UPSTREAM


def _compress_request_body(body: dict, provider: str) -> tuple[dict, list[dict]]:
    """Compress messages in the request body. Returns (compressed_body, stats)."""
    pipeline = CompressionPipeline()
    messages = body.get("messages", [])

    if not messages:
        return body, []

    compressed_msgs, compress_stats = pipeline.compress_messages(messages)
    body["messages"] = compressed_msgs
    return body, [s.__dict__ for s in compress_stats]


@app.get("/health")
async def health():
    return {"status": "ok", "service": "AITokenProxy", "version": "0.1.0"}


@app.get("/stats")
async def get_stats():
    """Return aggregate compression statistics."""
    total_original = 0
    total_compressed = 0
    total_requests = 0
    by_strategy: dict[str, dict] = {}

    for key, entries in stats_store.items():
        for entry in entries:
            total_requests += 1
            for stat in entry.get("stats", []):
                orig = stat.get("original_tokens", 0)
                comp = stat.get("compressed_tokens", 0)
                total_original += orig
                total_compressed += comp
                strategy = stat.get("strategy", "unknown")
                if strategy not in by_strategy:
                    by_strategy[strategy] = {"original": 0, "compressed": 0, "calls": 0}
                by_strategy[strategy]["original"] += orig
                by_strategy[strategy]["compressed"] += comp
                by_strategy[strategy]["calls"] += 1

    savings_pct = round((1 - total_compressed / total_original) * 100, 1) if total_original else 0.0
    estimated_savings = 0.0
    if total_original > total_compressed:
        saved_tokens = total_original - total_compressed
        # Rough estimate: assume GPT-4o pricing
        estimated_savings = (saved_tokens / 1_000_000) * 5.0  # $5 per 1M input tokens

    return {
        "total_requests": total_requests,
        "total_original_tokens": total_original,
        "total_compressed_tokens": total_compressed,
        "savings_pct": savings_pct,
        "estimated_cost_savings_usd": round(estimated_savings, 2),
        "by_strategy": by_strategy,
    }


@app.api_route("/openai/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_openai(request: Request, path: str):
    """Proxy OpenAI API requests with compression."""
    return await _proxy_request(request, path, "openai")


@app.api_route("/anthropic/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_anthropic(request: Request, path: str):
    """Proxy Anthropic API requests with compression."""
    return await _proxy_request(request, path, "anthropic")


async def _proxy_request(request: Request, path: str, provider: str):
    upstream_base = _get_upstream(f"/{provider}/")
    upstream_url = f"{upstream_base}/{path}"

    # Read body
    body_bytes = await request.body()
    body_dict: dict | None = None
    compress_stats: list[dict] = []

    if body_bytes and request.method in ("POST", "PUT"):
        try:
            body_dict = json.loads(body_bytes)
        except (json.JSONDecodeError, ValueError):
            pass

        # Only compress chat/completions endpoints
        if body_dict and ("chat" in path or "messages" in path):
            body_dict, compress_stats = _compress_request_body(body_dict, provider)
            body_bytes = json.dumps(body_dict).encode()

    # Forward headers (strip host, add auth from env if present)
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    # Use API key from environment if client didn't send one
    api_key = os.environ.get("OPENAI_API_KEY") if provider == "openai" else os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        if provider == "openai":
            headers["authorization"] = f"Bearer {api_key}"
        else:
            headers["x-api-key"] = api_key

    # Forward request
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.request(
                method=request.method,
                url=upstream_url,
                headers=headers,
                content=body_bytes,
                params=request.query_params,
            )
        except httpx.ConnectError:
            return JSONResponse(
                status_code=502,
                content={"error": f"Cannot connect to upstream {provider} API"},
            )

    # Record stats
    if compress_stats:
        stats_store[provider].append({
            "path": path,
            "timestamp": time.time(),
            "stats": compress_stats,
        })

    # Return response
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )
