"""Tests for AgentPulse models."""
from __future__ import annotations

from src.models import AgentEvent, BuildRecord, HealthRecord, CostRecord, SystemStats


class TestAgentEvent:
    def test_create_minimal(self):
        evt = AgentEvent(agent="forge", action="build", status="ok")
        assert evt.agent == "forge"
        assert evt.action == "build"

    def test_create_full(self):
        evt = AgentEvent(
            ts="2026-06-08T10:00:00Z",
            agent="lens",
            action="research",
            status="ok",
            confidence=0.95,
        )
        assert evt.confidence == 0.95


class TestBuildRecord:
    def test_create(self):
        b = BuildRecord(slug="test", status="success", cost_usd=1.5)
        assert b.slug == "test"
        assert b.cost_usd == 1.5


class TestHealthRecord:
    def test_create(self):
        h = HealthRecord(job_count=11, jobs={"email": "scheduled"})
        assert h.job_count == 11


class TestCostRecord:
    def test_create(self):
        c = CostRecord(cost_usd=2.5, agent="forge")
        assert c.cost_usd == 2.5


class TestSystemStats:
    def test_defaults(self):
        s = SystemStats()
        assert s.total_builds == 0
        assert s.active_agents == []
