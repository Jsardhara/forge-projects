"""Tests for RegShield API endpoints."""

import pytest
from fastapi.testclient import TestClient

from regshield.api import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealth:
    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "regshield"


class TestModels:
    def test_list_models(self, client):
        resp = client.get("/api/models")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0

    def test_get_model(self, client):
        resp = client.get("/api/models/openai/gpt-4o")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "GPT-4o"

    def test_get_unknown_model(self, client):
        resp = client.get("/api/models/nonexistent/model")
        assert resp.status_code == 404


class TestComplianceCheck:
    def test_check_compliant(self, client):
        resp = client.get(
            "/api/check?model_id=openai/gpt-4o&jurisdiction=US&use_case=general"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == "openai/gpt-4o"
        assert data["jurisdiction"] == "US"
        assert "risk_level" in data
        assert "is_allowed" in data

    def test_check_banned(self, client):
        resp = client.get(
            "/api/check?model_id=anthropic/claude-fable-5&jurisdiction=US"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_level"] == "banned"
        assert data["is_allowed"] is False

    def test_check_unknown_model(self, client):
        resp = client.get(
            "/api/check?model_id=nonexistent/model&jurisdiction=US"
        )
        assert resp.status_code == 404

    def test_check_invalid_jurisdiction(self, client):
        resp = client.get(
            "/api/check?model_id=openai/gpt-4o&jurisdiction=INVALID"
        )
        assert resp.status_code == 400


class TestStatuses:
    def test_list_statuses(self, client):
        resp = client.get("/api/statuses")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0

    def test_filter_by_jurisdiction(self, client):
        resp = client.get("/api/statuses?jurisdiction=US")
        assert resp.status_code == 200
        data = resp.json()
        assert all(s["jurisdiction"] == "US" for s in data)

    def test_filter_by_risk(self, client):
        resp = client.get("/api/statuses?risk_level=banned")
        assert resp.status_code == 200
        data = resp.json()
        assert all(s["risk_level"] == "banned" for s in data)


class TestAlerts:
    def test_list_alerts(self, client):
        resp = client.get("/api/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0

    def test_unread_alerts(self, client):
        resp = client.get("/api/alerts?unread_only=true")
        assert resp.status_code == 200

    def test_acknowledge_alert(self, client):
        # Get an unread alert
        resp = client.get("/api/alerts?unread_only=true")
        alerts = resp.json()
        if alerts:
            alert_id = alerts[0]["alert_id"]
            ack_resp = client.post(f"/api/alerts/{alert_id}/acknowledge")
            assert ack_resp.status_code == 200
            assert ack_resp.json()["acknowledged"] is True


class TestAuditLog:
    def test_audit_log(self, client):
        resp = client.get("/api/audit-log")
        assert resp.status_code == 200

    def test_audit_log_limit(self, client):
        resp = client.get("/api/audit-log?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 5


class TestDashboard:
    def test_dashboard_loads(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "RegShield" in resp.text
        assert "text/html" in resp.headers["content-type"]
