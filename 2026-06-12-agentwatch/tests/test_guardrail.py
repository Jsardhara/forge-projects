"""Tests for AgentWatch guardrail detection."""

import json
import pytest
from agentwatch.db import get_db, create_guardrail_probe, _create_tables
from agentwatch.guardrail import run_probe, get_drift_trend, ProbeResult
import sqlite3


@pytest.fixture
def mem_conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    _create_tables(c)
    return c


class TestRunProbe:
    def test_probe_passes_with_matching_keywords(self, mem_conn):
        create_guardrail_probe(
            mem_conn, "probe-1", "Test", "openai", "gpt-4o",
            "What is Python?", '["python", "programming", "machine learning"]'
        )
        result = run_probe(mem_conn, "probe-1")
        assert isinstance(result, ProbeResult)
        assert result.passed is True
        assert result.drift_score < 0.5

    def test_probe_fails_with_missing_keywords(self, mem_conn):
        create_guardrail_probe(
            mem_conn, "probe-1", "Test", "openai", "gpt-4o",
            "What is Python?", '["quantum", "blockchain", "defi", "nft", "web3"]'
        )
        result = run_probe(mem_conn, "probe-1")
        assert result.passed is False
        assert result.drift_score >= 0.5
        assert len(result.keywords_missing) > 0

    def test_probe_not_found_raises(self, mem_conn):
        with pytest.raises(ValueError, match="not found"):
            run_probe(mem_conn, "nonexistent")

    def test_probe_stores_result(self, mem_conn):
        create_guardrail_probe(
            mem_conn, "probe-1", "Test", "openai", "gpt-4o",
            "test", '["python"]'
        )
        run_probe(mem_conn, "probe-1")
        from agentwatch.db import get_guardrail_results
        results = get_guardrail_results(mem_conn, "probe-1")
        assert len(results) == 1

    def test_probe_with_custom_call_fn(self, mem_conn):
        create_guardrail_probe(
            mem_conn, "probe-1", "Test", "openai", "gpt-4o",
            "test", '["custom", "response"]'
        )
        def mock_call(prompt):
            return "This is a custom response with the right keywords."
        result = run_probe(mem_conn, "probe-1", call_model_fn=mock_call)
        assert "custom" in result.keywords_found
        assert "response" in result.keywords_found

    def test_probe_empty_keywords_always_passes(self, mem_conn):
        create_guardrail_probe(
            mem_conn, "probe-1", "Test", "openai", "gpt-4o",
            "test", '[]'
        )
        result = run_probe(mem_conn, "probe-1")
        assert result.passed is True
        assert result.drift_score == 0.0


class TestDriftTrend:
    def test_trend_empty(self, mem_conn):
        create_guardrail_probe(mem_conn, "probe-1", "Test", "openai", "gpt-4o", "test")
        trend = get_drift_trend(mem_conn, "probe-1")
        assert trend == []

    def test_trend_with_results(self, mem_conn):
        create_guardrail_probe(mem_conn, "probe-1", "Test", "openai", "gpt-4o", "test", '["python"]')
        run_probe(mem_conn, "probe-1")
        run_probe(mem_conn, "probe-1")
        trend = get_drift_trend(mem_conn, "probe-1")
        assert len(trend) == 2
        assert all("drift_score" in t for t in trend)
        assert all("passed" in t for t in trend)
