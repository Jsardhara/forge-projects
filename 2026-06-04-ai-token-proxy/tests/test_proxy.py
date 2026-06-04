"""Tests for the proxy server."""

import pytest
from httpx import AsyncClient, ASGITransport

from aitokenproxy.proxy import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "AITokenProxy"


@pytest.mark.anyio
async def test_stats_empty():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_requests"] == 0
    assert data["savings_pct"] == 0.0


@pytest.mark.anyio
async def test_openai_proxy_no_body():
    """Proxy endpoint should accept requests even without upstream."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/openai/v1/chat/completions", json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Hello"}]
        })
    # Should get 502 since no upstream, not a crash
    assert resp.status_code in (200, 502, 401)
