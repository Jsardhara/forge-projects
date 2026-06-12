"""Tests for AgentWatch database layer."""

import time
import pytest
from agentwatch.db import get_db, register_agent, list_agents, get_agent
from agentwatch.db import record_spend, get_spend, get_total_spend
from agentwatch.db import set_budget, get_budget
from agentwatch.db import create_guardrail_probe, list_guardrail_probes, get_guardrail_probe
from agentwatch.db import record_guardrail_result, get_guardrail_results
from agentwatch.db import create_alert, list_alerts, acknowledge_alert


@pytest.fixture
def conn():
    """Create a fresh in-memory database for each test."""
    return get_db(path=None)  # will use default, override below


@pytest.fixture
def mem_conn():
    """Create a fresh in-memory database for each test."""
    import sqlite3
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    from agentwatch.db import _create_tables
    _create_tables(c)
    return c


class TestAgentCRUD:
    def test_register_agent(self, mem_conn):
        result = register_agent(mem_conn, "agent-1", "Test Agent", "openai")
        assert result["agent_id"] == "agent-1"
        assert result["name"] == "Test Agent"
        assert result["provider"] == "openai"

    def test_list_agents(self, mem_conn):
        register_agent(mem_conn, "a1", "Agent One", "openai")
        register_agent(mem_conn, "a2", "Agent Two", "anthropic")
        agents = list_agents(mem_conn)
        assert len(agents) == 2

    def test_get_agent(self, mem_conn):
        register_agent(mem_conn, "agent-1", "Test Agent", "openai")
        agent = get_agent(mem_conn, "agent-1")
        assert agent is not None
        assert agent["name"] == "Test Agent"

    def test_get_agent_not_found(self, mem_conn):
        assert get_agent(mem_conn, "nonexistent") is None


class TestSpendTracking:
    def test_record_spend(self, mem_conn):
        register_agent(mem_conn, "agent-1", "Test Agent")
        result = record_spend(mem_conn, "agent-1", 1000, 500, 0.003)
        assert result["cost_usd"] == 0.003
        assert result["tokens_in"] == 1000

    def test_get_spend(self, mem_conn):
        register_agent(mem_conn, "agent-1", "Test Agent")
        record_spend(mem_conn, "agent-1", 100, 50, 0.001)
        record_spend(mem_conn, "agent-1", 200, 100, 0.002)
        records = get_spend(mem_conn, "agent-1")
        assert len(records) == 2

    def test_get_total_spend(self, mem_conn):
        register_agent(mem_conn, "agent-1", "Test Agent")
        record_spend(mem_conn, "agent-1", 100, 50, 0.001)
        record_spend(mem_conn, "agent-1", 200, 100, 0.002)
        total = get_total_spend(mem_conn, "agent-1")
        assert total == 0.003

    def test_get_total_spend_empty(self, mem_conn):
        register_agent(mem_conn, "agent-1", "Test Agent")
        total = get_total_spend(mem_conn, "agent-1")
        assert total == 0.0

    def test_get_spend_with_since(self, mem_conn):
        register_agent(mem_conn, "agent-1", "Test Agent")
        record_spend(mem_conn, "agent-1", 100, 50, 0.001)
        now = time.time()
        records = get_spend(mem_conn, "agent-1", since=now - 1)
        assert len(records) == 1


class TestBudget:
    def test_set_budget(self, mem_conn):
        register_agent(mem_conn, "agent-1", "Test Agent")
        result = set_budget(mem_conn, "agent-1", daily_limit_usd=10.0, monthly_limit_usd=200.0, alert_threshold_pct=75.0)
        assert result["daily_limit_usd"] == 10.0
        assert result["monthly_limit_usd"] == 200.0
        assert result["alert_threshold_pct"] == 75.0

    def test_get_budget(self, mem_conn):
        register_agent(mem_conn, "agent-1", "Test Agent")
        set_budget(mem_conn, "agent-1", 10.0, 200.0)
        budget = get_budget(mem_conn, "agent-1")
        assert budget is not None
        assert budget["daily_limit_usd"] == 10.0

    def test_get_budget_not_found(self, mem_conn):
        assert get_budget(mem_conn, "nonexistent") is None

    def test_default_budget_on_register(self, mem_conn):
        register_agent(mem_conn, "agent-1", "Test Agent")
        budget = get_budget(mem_conn, "agent-1")
        assert budget is not None
        assert budget["daily_limit_usd"] == 5.0
        assert budget["monthly_limit_usd"] == 100.0


class TestGuardrailProbes:
    def test_create_probe(self, mem_conn):
        result = create_guardrail_probe(
            mem_conn, "probe-1", "Test Probe", "openai", "gpt-4o",
            "What is Python?", '["python", "programming"]'
        )
        assert result["probe_id"] == "probe-1"
        assert result["name"] == "Test Probe"

    def test_list_probes(self, mem_conn):
        create_guardrail_probe(mem_conn, "p1", "Probe 1", "openai", "gpt-4o", "test")
        create_guardrail_probe(mem_conn, "p2", "Probe 2", "anthropic", "claude-sonnet-4", "test")
        probes = list_guardrail_probes(mem_conn)
        assert len(probes) == 2

    def test_get_probe(self, mem_conn):
        create_guardrail_probe(mem_conn, "probe-1", "Test", "openai", "gpt-4o", "test")
        probe = get_guardrail_probe(mem_conn, "probe-1")
        assert probe is not None
        assert probe["name"] == "Test"

    def test_get_probe_not_found(self, mem_conn):
        assert get_guardrail_probe(mem_conn, "nonexistent") is None


class TestGuardrailResults:
    def test_record_result(self, mem_conn):
        create_guardrail_probe(mem_conn, "probe-1", "Test", "openai", "gpt-4o", "test")
        result = record_guardrail_result(
            mem_conn, "probe-1", "response text", '["found"]', '["missing"]', 0.5, True
        )
        assert result["passed"] is True
        assert result["drift_score"] == 0.5

    def test_get_results(self, mem_conn):
        create_guardrail_probe(mem_conn, "probe-1", "Test", "openai", "gpt-4o", "test")
        record_guardrail_result(mem_conn, "probe-1", "r1", "[]", "[]", 0.0, True)
        record_guardrail_result(mem_conn, "probe-1", "r2", "[]", "[]", 0.1, True)
        results = get_guardrail_results(mem_conn, "probe-1")
        assert len(results) == 2


class TestAlerts:
    def test_create_alert(self, mem_conn):
        result = create_alert(mem_conn, "budget_warning", "Test alert", "warn", agent_id="agent-1")
        assert result["alert_type"] == "budget_warning"
        assert result["severity"] == "warn"

    def test_list_alerts(self, mem_conn):
        create_alert(mem_conn, "test", "Alert 1", "warn")
        create_alert(mem_conn, "test", "Alert 2", "alert")
        alerts = list_alerts(mem_conn)
        assert len(alerts) == 2

    def test_list_alerts_unread(self, mem_conn):
        create_alert(mem_conn, "test", "Alert 1", "warn")
        create_alert(mem_conn, "test", "Alert 2", "alert")
        alerts = list_alerts(mem_conn, unread_only=True)
        assert len(alerts) == 2

    def test_acknowledge_alert(self, mem_conn):
        create_alert(mem_conn, "test", "Alert 1", "warn")
        alerts = list_alerts(mem_conn, unread_only=True)
        assert len(alerts) == 1
        ok = acknowledge_alert(mem_conn, alerts[0]["id"])
        assert ok is True
        alerts = list_alerts(mem_conn, unread_only=True)
        assert len(alerts) == 0
