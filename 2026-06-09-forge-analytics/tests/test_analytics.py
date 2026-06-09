"""Tests for analytics.py."""
from __future__ import annotations

import pytest

from forge_analytics.analytics import compute_summary, filter_runs, trend_line
from forge_analytics.models import BuildRun


def _make_run(**kwargs):
    defaults = dict(
        date="2026-06-08", slug="test", title="Test", folder="test",
        repo_url="", commit_sha="", cost_usd=1.0, duration_sec=100.0,
        status="success", error=None, timestamp=None,
    )
    defaults.update(kwargs)
    return BuildRun(**defaults)


class TestComputeSummary:
    def test_empty_runs(self):
        s = compute_summary([])
        assert s.total_builds == 0
        assert s.successful_builds == 0

    def test_successful_builds(self):
        runs = [
            _make_run(slug="a", status="success", cost_usd=1.0, duration_sec=100),
            _make_run(slug="b", status="success", cost_usd=2.0, duration_sec=200),
            _make_run(slug="c", status="failed", cost_usd=0.5, duration_sec=50),
            _make_run(slug="d", status="skipped_budget", cost_usd=0, duration_sec=0),
        ]
        s = compute_summary(runs)
        assert s.total_builds == 4
        assert s.successful_builds == 2
        assert s.failed_builds == 1
        assert s.skipped_builds == 1
        assert s.total_cost_usd == 3.5
        # avg is computed over non-zero cost runs: 3.5 / 3 = 1.1667
        assert s.avg_cost_usd == pytest.approx(1.1667, abs=0.01)

    def test_most_expensive(self):
        runs = [
            _make_run(slug="cheap", cost_usd=0.1),
            _make_run(slug="expensive", cost_usd=5.0),
            _make_run(slug="mid", cost_usd=1.0),
        ]
        s = compute_summary(runs)
        assert s.most_expensive.slug == "expensive"

    def test_most_longest(self):
        runs = [
            _make_run(slug="short", duration_sec=10),
            _make_run(slug="long", duration_sec=600),
            _make_run(slug="mid", duration_sec=100),
        ]
        s = compute_summary(runs)
        assert s.longest.slug == "long"

    def test_error_frequency(self):
        runs = [
            _make_run(slug="a", status="failed", error="timeout"),
            _make_run(slug="b", status="failed", error="timeout"),
            _make_run(slug="c", status="failed", error="429 rate limit"),
        ]
        s = compute_summary(runs)
        assert s.most_common_error == "timeout"
        assert s.error_counts["timeout"] == 2

    def test_builds_by_date(self):
        runs = [
            _make_run(date="2026-06-08", slug="a"),
            _make_run(date="2026-06-08", slug="b"),
            _make_run(date="2026-06-09", slug="c"),
        ]
        s = compute_summary(runs)
        assert s.builds_by_date["2026-06-08"] == 2
        assert s.builds_by_date["2026-06-09"] == 1

    def test_date_range(self):
        runs = [
            _make_run(date="2026-06-01", slug="a"),
            _make_run(date="2026-06-05", slug="b"),
            _make_run(date="2026-06-03", slug="c"),
        ]
        s = compute_summary(runs)
        assert s.date_range_start == "2026-06-01"
        assert s.date_range_end == "2026-06-05"

    def test_cost_by_date(self):
        runs = [
            _make_run(date="2026-06-08", cost_usd=2.0),
            _make_run(date="2026-06-08", cost_usd=3.0),
            _make_run(date="2026-06-09", cost_usd=1.0),
        ]
        s = compute_summary(runs)
        assert s.cost_by_date["2026-06-08"] == 5.0
        assert s.cost_by_date["2026-06-09"] == 1.0


class TestFilterRuns:
    def test_filter_by_date_range(self):
        runs = [
            _make_run(date="2026-06-07", slug="a"),
            _make_run(date="2026-06-08", slug="b"),
            _make_run(date="2026-06-09", slug="c"),
        ]
        result = filter_runs(runs, since="2026-06-08")
        assert len(result) == 2

    def test_filter_by_status(self):
        runs = [
            _make_run(slug="a", status="success"),
            _make_run(slug="b", status="failed"),
            _make_run(slug="c", status="success"),
        ]
        result = filter_runs(runs, status="success")
        assert len(result) == 2

    def test_combined_filters(self):
        runs = [
            _make_run(date="2026-06-07", slug="a", status="success"),
            _make_run(date="2026-06-08", slug="b", status="failed"),
            _make_run(date="2026-06-08", slug="c", status="success"),
        ]
        result = filter_runs(runs, since="2026-06-08", status="success")
        assert len(result) == 1
        assert result[0].slug == "c"


class TestTrendLine:
    def test_up_trend(self):
        assert trend_line([1.0, 1.1, 1.2, 1.5, 2.0, 2.5]) == "up"

    def test_down_trend(self):
        assert trend_line([2.5, 2.0, 1.5, 1.2, 1.1, 1.0]) == "down"

    def test_flat_trend(self):
        assert trend_line([1.0, 1.05, 0.95, 1.02, 0.98]) == "flat"

    def test_insufficient_data(self):
        assert trend_line([1.0, 2.0]) == "insufficient_data"
