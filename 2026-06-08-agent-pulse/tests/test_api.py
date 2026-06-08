"""Tests for AgentPulse API endpoints."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    """Create a test client with isolated temp data."""
    state_dir = tmp_path / "state"
    bus_dir = tmp_path / "bus" / "inbox"
    state_dir.mkdir(parents=True)
    bus_dir.mkdir(parents=True)

    # Write test data
    (state_dir / "agent_log.jsonl").write_text(json.dumps({
        "ts": "2026-06-08T10:00:00Z",
        "agent": "forge",
        "action": "build",
        "status": "ok",
    }) + "\n")

    (state_dir / "daily_projects.jsonl").write_text(json.dumps({
        "ts": "2026-06-08T10:00:00Z",
        "date": "2026-06-08",
        "status": "success",
        "slug": "test-project",
        "title": "Test Project",
        "cost_usd": 1.5,
    }) + "\n")

    (state_dir / "sentinel_health.jsonl").write_text(json.dumps({
        "ts": "2026-06-08T10:00:00Z",
        "job_count": 11,
        "jobs": {"email": "scheduled", "forge": "scheduled"},
    }) + "\n")

    (state_dir / "cost_log.jsonl").write_text(json.dumps({
        "ts": "2026-06-08T10:00:00Z",
        "agent": "forge",
        "cost_usd": 1.5,
    }) + "\n")

    # Set env vars BEFORE importing the app
    os.environ["AGENTPULSE_STATE_DIR"] = str(state_dir)
    os.environ["AGENTPULSE_BUS_DIR"] = str(bus_dir.parent)

    # Force reimport of readers module to pick up env vars
    import importlib
    import src.readers
    importlib.reload(src.readers)

    from src.main import app
    test_client = TestClient(app)

    yield test_client

    # Cleanup env vars
    os.environ.pop("AGENTPULSE_STATE_DIR", None)
    os.environ.pop("AGENTPULSE_BUS_DIR", None)


class TestApiEndpoints:
    def test_agents_endpoint(self, client):
        response = client.get("/api/agents")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["agent"] == "forge"

    def test_builds_endpoint(self, client):
        response = client.get("/api/builds")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["slug"] == "test-project"

    def test_health_endpoint(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["job_count"] == 11

    def test_costs_endpoint(self, client):
        response = client.get("/api/costs")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["cost_usd"] == 1.5

    def test_stats_endpoint(self, client):
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_builds"] >= 1
        assert data["successful_builds"] >= 1
        assert "active_agents" in data

    def test_all_endpoint(self, client):
        response = client.get("/api/all")
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert "builds" in data
        assert "agents" in data
        assert "health" in data
        assert "bus" in data

    def test_dashboard_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "AgentPulse" in response.text

    def test_agents_limit_param(self, client):
        response = client.get("/api/agents?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 1
