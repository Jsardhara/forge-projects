"""Integration tests for AgentOS API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from agentos.main import app
from agentos.models import init_db


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(f"sqlite:///{db_path}")
    yield


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


@pytest.mark.anyio
async def test_create_and_list_agents():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create agent
        resp = await client.post(
            "/api/agents",
            json={
                "id": "claude-1",
                "name": "Claude Code",
                "agent_type": "claude_code",
                "max_spend_per_run": 2.0,
                "max_daily_spend": 20.0,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "created"

        # List agents
        resp = await client.get("/api/agents")
        assert resp.status_code == 200
        agents = resp.json()
        assert len(agents) == 1
        assert agents[0]["id"] == "claude-1"

        # Get specific agent
        resp = await client.get("/api/agents/claude-1")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Claude Code"


@pytest.mark.anyio
async def test_create_and_check_policy():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create agent first
        await client.post(
            "/api/agents",
            json={"id": "agent-test", "name": "Test Agent", "agent_type": "custom"},
        )

        # Create policy
        resp = await client.post(
            "/api/policies",
            json={
                "id": "pol-test",
                "name": "Test Policy",
                "scope": "global",
                "max_spend_per_run": 1.0,
                "blocked_tools": "rm,exec",
            },
        )
        assert resp.status_code == 200

        # Check policy — allowed
        resp = await client.post(
            "/api/policies/check",
            json={
                "agent_id": "agent-test",
                "estimated_cost": 0.5,
                "tools_requested": ["read_file"],
            },
        )
        assert resp.status_code == 200
        result = resp.json()
        assert result["decision"] == "allow"

        # Check policy — blocked tool
        resp = await client.post(
            "/api/policies/check",
            json={
                "agent_id": "agent-test",
                "tools_requested": ["rm"],
            },
        )
        result = resp.json()
        assert result["decision"] == "block"


@pytest.mark.anyio
async def test_audit_and_cost_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create agent
        await client.post(
            "/api/agents",
            json={"id": "audit-test", "name": "Audit Agent", "agent_type": "codex"},
        )

        # Record audit entry
        resp = await client.post(
            "/api/audit",
            json={
                "agent_id": "audit-test",
                "action": "code_review",
                "cost": 0.05,
                "tokens_in": 1000,
                "tokens_out": 500,
                "policy_decision": "allow",
            },
        )
        assert resp.status_code == 200

        # List audit logs
        resp = await client.get("/api/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

        # Record cost
        resp = await client.post(
            "/api/costs",
            json={
                "agent_id": "audit-test",
                "amount": 0.05,
                "tokens_in": 1000,
                "tokens_out": 500,
            },
        )
        assert resp.status_code == 200

        # Get cost summary
        resp = await client.get("/api/costs")
        assert resp.status_code == 200
        summary = resp.json()
        assert summary["total_cost"] >= 0.05


@pytest.mark.anyio
async def test_dashboard_html():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "AgentOS" in resp.text
