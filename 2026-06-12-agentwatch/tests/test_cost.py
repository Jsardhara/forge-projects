"""Tests for AgentWatch cost tracking."""

import time
import pytest
from agentwatch.db import get_db, register_agent, record_spend, _create_tables
from agentwatch.cost import check_budget, estimate_cost, SpendReport
import sqlite3


@pytest.fixture
def mem_conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    _create_tables(c)
    return c


class TestEstimateCost:
    def test_gpt4o_pricing(self):
        cost = estimate_cost(1000, 500, "gpt-4o")
        expected = (1000 * 2.50 + 500 * 10.00) / 1_000_000
        assert abs(cost - expected) < 1e-10

    def test_gpt4o_mini_pricing(self):
        cost = estimate_cost(10000, 5000, "gpt-4o-mini")
        expected = (10000 * 0.15 + 5000 * 0.60) / 1_000_000
        assert abs(cost - expected) < 1e-10

    def test_claude_sonnet_pricing(self):
        cost = estimate_cost(1000, 500, "claude-sonnet-4")
        expected = (1000 * 3.00 + 500 * 15.00) / 1_000_000
        assert abs(cost - expected) < 1e-10

    def test_unknown_model_defaults_to_gpt4o(self):
        cost = estimate_cost(1000, 500, "unknown-model")
        expected = (1000 * 2.50 + 500 * 10.00) / 1_000_000
        assert abs(cost - expected) < 1e-10

    def test_zero_tokens(self):
        assert estimate_cost(0, 0, "gpt-4o") == 0.0


class TestCheckBudget:
    def test_no_spend(self, mem_conn):
        register_agent(mem_conn, "agent-1", "Test")
        report = check_budget(mem_conn, "agent-1")
        assert report.daily_spend == 0.0
        assert report.monthly_spend == 0.0
        assert report.budget_exceeded is False
        assert report.alert_triggered is False

    def test_under_budget(self, mem_conn):
        register_agent(mem_conn, "agent-1", "Test")
        record_spend(mem_conn, "agent-1", 1000, 500, 1.0)
        report = check_budget(mem_conn, "agent-1")
        assert report.daily_spend == 1.0
        assert report.budget_exceeded is False
        assert report.alert_triggered is False

    def test_alert_threshold(self, mem_conn):
        register_agent(mem_conn, "agent-1", "Test")
        # Default budget: daily $5, threshold 80% = $4
        record_spend(mem_conn, "agent-1", 1000, 500, 4.5)
        report = check_budget(mem_conn, "agent-1")
        assert report.alert_triggered is True
        assert report.budget_exceeded is False

    def test_budget_exceeded(self, mem_conn):
        register_agent(mem_conn, "agent-1", "Test")
        # Default budget: daily $5
        record_spend(mem_conn, "agent-1", 1000, 500, 6.0)
        report = check_budget(mem_conn, "agent-1")
        assert report.budget_exceeded is True

    def test_report_fields(self, mem_conn):
        register_agent(mem_conn, "agent-1", "Test")
        report = check_budget(mem_conn, "agent-1")
        assert isinstance(report, SpendReport)
        assert report.agent_id == "agent-1"
        assert report.daily_limit == 5.0
        assert report.monthly_limit == 100.0
