"""Tests for reporter.py."""
from __future__ import annotations

from forge_analytics.analytics import compute_summary
from forge_analytics.models import BuildRun
from forge_analytics.reporter import _fmt_duration, _generate_recommendations, generate_markdown_report


def _make_run(**kwargs):
    defaults = dict(
        date="2026-06-08", slug="test", title="Test", folder="test",
        repo_url="", commit_sha="", cost_usd=1.0, duration_sec=100.0,
        status="success", error=None, timestamp=None,
    )
    defaults.update(kwargs)
    return BuildRun(**defaults)


class TestFmtDuration:
    def test_seconds(self):
        assert _fmt_duration(45) == "45s"

    def test_minutes(self):
        assert _fmt_duration(300) == "5.0m"

    def test_hours(self):
        assert _fmt_duration(7200) == "2.0h"


class TestGenerateRecommendations:
    def test_no_data(self):
        s = compute_summary([])
        recs = _generate_recommendations(s)
        assert len(recs) == 1
        assert "No build data" in recs[0]

    def test_high_failure_rate(self):
        runs = [
            _make_run(slug="a", status="failed", error="timeout"),
            _make_run(slug="b", status="failed", error="timeout"),
            _make_run(slug="c", status="failed", error="429"),
            _make_run(slug="d", status="success"),
        ]
        s = compute_summary(runs)
        recs = _generate_recommendations(s)
        assert any("failure rate" in r.lower() for r in recs)

    def test_long_builds(self):
        runs = [
            _make_run(slug="a", duration_sec=900, cost_usd=1.0),
            _make_run(slug="b", duration_sec=800, cost_usd=1.0),
        ]
        s = compute_summary(runs)
        recs = _generate_recommendations(s)
        assert any("duration" in r.lower() for r in recs)

    def test_expensive_outlier(self):
        runs = [
            _make_run(slug="cheap1", cost_usd=0.1, duration_sec=10),
            _make_run(slug="cheap2", cost_usd=0.1, duration_sec=10),
            _make_run(slug="expensive", cost_usd=20.0, duration_sec=10),
        ]
        s = compute_summary(runs)
        recs = _generate_recommendations(s)
        assert any("expensive" in r.lower() or "outlier" in r.lower() or "cost" in r.lower() for r in recs)

    def test_skipped_builds(self):
        runs = [
            _make_run(slug="a", status="success"),
            _make_run(slug="b", status="skipped_budget"),
        ]
        s = compute_summary(runs)
        recs = _generate_recommendations(s)
        assert any("skipped" in r.lower() for r in recs)


class TestGenerateMarkdownReport:
    def test_empty_runs(self):
        report = generate_markdown_report([], reads_total=0, reads_errors=0)
        assert "# Forge Analytics Report" in report
        assert "Total builds | 0" in report

    def test_with_builds(self):
        runs = [
            _make_run(date="2026-06-07", slug="a", cost_usd=1.0, duration_sec=100, status="success"),
            _make_run(date="2026-06-08", slug="b", cost_usd=2.0, duration_sec=200, status="success"),
        ]
        report = generate_markdown_report(runs, reads_total=2, reads_errors=0)
        assert "# Forge Analytics Report" in report
        assert "Total builds | 2" in report
        assert "2026-06-07" in report
        assert "2026-06-08" in report
        assert "Recommendations" in report

    def test_with_errors(self):
        runs = [
            _make_run(slug="a", status="failed", error="timeout"),
            _make_run(slug="b", status="success"),
        ]
        report = generate_markdown_report(runs, reads_total=2, reads_errors=0)
        assert "Error Analysis" in report
        assert "timeout" in report

    def test_data_quality_section(self):
        report = generate_markdown_report([], reads_total=10, reads_errors=2)
        assert "Data Quality" in report
        assert "Parse errors: 2" in report
