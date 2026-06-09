"""Tests for readers.py."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from forge_analytics.readers import _read_jsonl, read_build_runs, read_forge_runs


class TestReadJsonl:
    def test_reads_valid_jsonl(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps({"a": 1}) + "\n")
            f.write(json.dumps({"b": 2}) + "\n")
            f.flush()
            results, total, errors = _read_jsonl(f.name)
            assert total == 2
            assert errors == 0
            assert len(results) == 2
            assert results[0]["a"] == 1
            assert results[1]["b"] == 2
        Path(f.name).unlink()

    def test_skips_empty_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps({"a": 1}) + "\n")
            f.write("\n")
            f.write(json.dumps({"b": 2}) + "\n")
            f.flush()
            results, total, errors = _read_jsonl(f.name)
            assert total == 2
            assert len(results) == 2
        Path(f.name).unlink()

    def test_handles_malformed_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps({"a": 1}) + "\n")
            f.write("this is not json\n")
            f.write(json.dumps({"b": 2}) + "\n")
            f.flush()
            results, total, errors = _read_jsonl(f.name)
            assert total == 3
            assert errors == 1
            assert len(results) == 2
        Path(f.name).unlink()

    def test_missing_file_returns_empty(self):
        results, total, errors = _read_jsonl("/tmp/nonexistent_12345.jsonl")
        assert total == 0
        assert errors == 0
        assert results == []


class TestReadBuildRuns:
    def test_reads_build_runs(self):
        record = {
            "ts": "2026-06-08T06:32:00.000000+00:00",
            "date": "2026-06-08",
            "slug": "agent-pulse",
            "title": "AgentPulse",
            "folder": "2026-06-08-agent-pulse",
            "repo_url": "https://github.com/Jsardhara/forge-projects",
            "commit_sha": "abc123",
            "cost_usd": 2.5,
            "duration_sec": 300.0,
            "status": "success",
            "error": None,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps(record) + "\n")
            f.flush()
            runs, total, errors = read_build_runs(f.name)
            assert total == 1
            assert errors == 0
            assert len(runs) == 1
            assert runs[0].slug == "agent-pulse"
            assert runs[0].cost_usd == 2.5
            assert runs[0].status == "success"
        Path(f.name).unlink()

    def test_handles_bad_records_gracefully(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps({"date": "2026-06-08", "slug": "test", "title": "Test",
                                "folder": "test", "repo_url": "", "commit_sha": "",
                                "cost_usd": 1.0, "duration_sec": 100.0,
                                "status": "success", "error": None}) + "\n")
            f.write("garbage\n")
            f.write(json.dumps({"date": "2026-06-09", "slug": "test2", "title": "Test2",
                                "folder": "test2", "repo_url": "", "commit_sha": "",
                                "cost_usd": 2.0, "duration_sec": 200.0,
                                "status": "failed", "error": "timeout"}) + "\n")
            f.flush()
            runs, total, errors = read_build_runs(f.name)
            assert len(runs) == 2
            assert errors >= 1
        Path(f.name).unlink()


class TestReadForgeRuns:
    def test_reads_forge_runs(self):
        record = {
            "run_id": "abc123",
            "repo_path": "/c/Users/jyot2/jarvis",
            "branch": "main",
            "task": "Build something useful",
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps(record) + "\n")
            f.flush()
            entries, total, errors = read_forge_runs(f.name)
            assert total == 1
            assert len(entries) == 1
            assert entries[0].run_id == "abc123"
        Path(f.name).unlink()
