"""Tests for cli.py."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

from forge_analytics.cli import main


def _write_daily_projects(path: Path, records: list[dict]):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _make_record(**kwargs):
    defaults = dict(
        ts="2026-06-08T06:32:00.000000+00:00",
        date="2026-06-08",
        slug="test-build",
        title="Test Build",
        folder="test",
        repo_url="",
        commit_sha="abc123",
        cost_usd=1.0,
        duration_sec=100.0,
        status="success",
        error=None,
    )
    defaults.update(kwargs)
    return defaults


class TestReportCommand:
    def test_report_json(self):
        record = _make_record()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily_projects.jsonl"
            _write_daily_projects(path, [record])

            runner = CliRunner()
            result = runner.invoke(main, ["report", "--state-dir", tmp, "--json-output"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["total_builds"] == 1
            assert data["successful_builds"] == 1

    def test_report_markdown(self):
        record = _make_record()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily_projects.jsonl"
            _write_daily_projects(path, [record])

            runner = CliRunner()
            result = runner.invoke(main, ["report", "--state-dir", tmp])
            assert result.exit_code == 0
            assert "# Forge Analytics Report" in result.output

    def test_report_with_filters(self):
        records = [
            _make_record(date="2026-06-07", slug="a", status="success"),
            _make_record(date="2026-06-08", slug="b", status="failed"),
            _make_record(date="2026-06-09", slug="c", status="success"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily_projects.jsonl"
            _write_daily_projects(path, records)

            runner = CliRunner()
            result = runner.invoke(
                main, ["report", "--state-dir", tmp, "--since", "2026-06-08", "--json-output"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["total_builds"] == 2

    def test_report_empty_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily_projects.jsonl"
            path.write_text("")

            runner = CliRunner()
            result = runner.invoke(main, ["report", "--state-dir", tmp, "--json-output"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["total_builds"] == 0

    def test_report_output_file(self):
        record = _make_record()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily_projects.jsonl"
            _write_daily_projects(path, [record])
            out_path = Path(tmp) / "report.md"

            runner = CliRunner()
            result = runner.invoke(
                main, ["report", "--state-dir", tmp, "-o", str(out_path)]
            )
            assert result.exit_code == 0
            assert out_path.exists()
            content = out_path.read_text()
            assert "# Forge Analytics Report" in content


class TestStatusCommand:
    def test_status(self):
        record = _make_record(date="2026-06-08", slug="latest-build")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily_projects.jsonl"
            _write_daily_projects(path, [record])

            runner = CliRunner()
            result = runner.invoke(main, ["status", "--state-dir", tmp])
            assert result.exit_code == 0
            assert "latest-build" in result.output
            assert "success" in result.output

    def test_status_no_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = CliRunner()
            result = runner.invoke(main, ["status", "--state-dir", tmp])
            assert result.exit_code == 0
            assert "No build data" in result.output
