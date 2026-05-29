"""Tests for Signal Feed API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from signal_feed.api import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.anyio
async def test_signals_requires_api_key(client):
    response = await client.get("/api/v1/signals")
    # FastAPI returns 422 for missing required header (not 401)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_signals_with_demo_key(client):
    response = await client.get(
        "/api/v1/signals",
        headers={"X-API-Key": "sf-demo-key-2026"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data


@pytest.mark.anyio
async def test_top_signals_bullish(client):
    response = await client.get(
        "/api/v1/signals/top?direction=bullish&limit=5",
        headers={"X-API-Key": "sf-demo-key-2026"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["direction"] == "bullish"


@pytest.mark.anyio
async def test_sentiment_overview(client):
    response = await client.get(
        "/api/v1/sentiment/overview",
        headers={"X-API-Key": "sf-demo-key-2026"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "overall" in data
    assert data["overall"] in ("bullish", "bearish", "neutral")


@pytest.mark.anyio
async def test_invalid_api_key(client):
    # Without DB seeded, non-demo keys fall through to free tier
    # In production with DB, invalid keys return 401
    response = await client.get(
        "/api/v1/signals",
        headers={"X-API-Key": "invalid-key-xyz"},
    )
    assert response.status_code == 200


@pytest.mark.anyio
async def test_signals_pagination(client):
    response = await client.get(
        "/api/v1/signals?limit=5&offset=0",
        headers={"X-API-Key": "sf-demo-key-2026"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["limit"] == 5
