"""Tests for AgentPulse readers."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.readers import (
    read_jsonl,
    read_agent_log,
    read_builds,
    read_health,
    read_costs,
    compute_stats,
)


@pytest.fixture
def tmp_state(tmp_path):
    """Create a temporary state directory with test data."""
    return tmp_path


class TestReadJsonl:
    def test_reads_valid_jsonl(self, tmp_state):
        data = [{"a": 1}, {"a": 2}, {"a": 3}]
        path = tmp_state / "test.jsonl"
        path.write_text("\n".join(json.dumps(d) for d in data))
        result = read_jsonl("test.jsonl", state_dir=tmp_state)
        assert len(result) == 3
        assert result[0]["a"] == 1

    def test_returns_empty_for_missing_file(self, tmp_state):
        result = read_jsonl("nonexistent.jsonl", state_dir=tmp_state)
        assert result == []

    def test_skips_corrupt_lines(self, tmp_state):
        path = tmp_state / "test.jsonl"
        path.write_text('{"a": 1}\nNOT_JSON\n{"a": 2}')
        result = read_jsonl("test.jsonl", state_dir=tmp_state)
        assert len(result) == 2

    def test_last_n_limits_results(self, tmp_state):
        data = [{"i": i} for i in range(100)]
        path = tmp_state / "test.jsonl"
        path.write_text("\n".join(json.dumps(d) for d in data))
        result = read_jsonl("test.jsonl", state_dir=tmp_state, last_n=5)
        assert len(result) == 5
        assert result[-1]["i"] == 99

    def test_empty_lines_skipped(self, tmp_state):
        path = tmp_state / "test.jsonl"
        path.write_text('{"a": 1}\n\n{"a": 2}\n')
        result = read_jsonl("test.jsonl", state_dir=tmp_state)
        assert len(result) == 2


class TestComputeStats:
    def test_empty_data(self):
        stats = compute_stats([], [], [], [])
        assert stats["total_builds"] == 0
        assert stats["successful_builds"] == 0
        assert stats["total_cost_usd"] == 0.0
        assert stats["active_agents"] == []

    def test_build_counts(self):
        builds = [
            {"status": "success", "date": "2026-06-08"},
            {"status": "success", "date": "2026-06-07"},
            {"status": "failed", "date": "2026-06-06"},
        ]
        stats = compute_stats(builds, [], [], [])
        assert stats["total_builds"] == 3
        assert stats["successful_builds"] == 2
        assert stats["failed_builds"] == 1

    def test_cost_aggregation(self):
        costs = [
            {"cost_usd": 1.5},
            {"cost_usd": 2.3},
            {"cost_usd": None},
        ]
        stats = compute_stats([], [], costs, [])
        assert stats["total_cost_usd"] == 3.8

    def test_active_agents(self):
        events = [
            {"agent": "forge"},
            {"agent": "lens"},
            {"agent": "forge"},
            {"agent": "sentinel"},
        ]
        stats = compute_stats([], events, [], [])
        assert stats["active_agents"] == ["forge", "lens", "sentinel"]
        assert stats["total_agent_events"] == 4

    def test_last_build(self):
        builds = [
            {"status": "success", "date": "2026-06-06", "slug": "old"},
            {"status": "success", "date": "2026-06-08", "slug": "new"},
        ]
        stats = compute_stats(builds, [], [], [])
        assert stats["last_build_date"] == "2026-06-08"
        assert stats["last_build_status"] == "success"

    def test_sentinel_jobs(self):
        health = [{"job_count": 11}]
        stats = compute_stats([], [], [], health)
        assert stats["sentinel_jobs"] == 11

    def test_failed_status_variants(self):
        builds = [
            {"status": "failed"},
            {"status": "error"},
            {"status": "success"},
        ]
        stats = compute_stats(builds, [], [], [])
        assert stats["failed_builds"] == 2
        assert stats["successful_builds"] == 1
