"""Tests for healthpulse.aggregator module."""

import datetime as dt
import pytest

from healthpulse.aggregator import (
    aggregate_jobs,
    aggregate_error_patterns,
    build_system_health,
    _error_signature,
)
from healthpulse.models import HealthStatus, LogEntry


def _entry(
    level="INFO",
    source="test",
    message="test message",
    ts=None,
    job_name=None,
    is_error=False,
    is_success=False,
    traceback=None,
):
    return LogEntry(
        timestamp=ts or dt.datetime(2026, 6, 5, 12, 0, 0),
        level=level,
        source=source,
        message=message,
        raw=f"{level} {source}: {message}",
        job_name=job_name,
        is_error=is_error,
        is_success=is_success,
        traceback=traceback,
    )


class TestErrorSignature:
    def test_basic(self):
        sig = _error_signature("ValueError: invalid literal for int()")
        assert "ValueError" in sig

    def test_normalizes_numbers(self):
        sig = _error_signature("Error at line 42 in file 123")
        assert "<n>" in sig
        assert "42" not in sig

    def test_with_traceback(self):
        tb = 'Traceback:\n  File "test.py", line 10\nValueError: invalid literal'
        sig = _error_signature("some message", tb)
        assert "ValueError" in sig

    def test_truncation(self):
        long_msg = "x" * 300
        sig = _error_signature(long_msg)
        assert len(sig) <= 200


class TestAggregateJobs:
    def test_healthy_job(self):
        entries = [
            _entry(message='Running job "email_tick"', job_name="email_tick"),
            _entry(message='Job "email_tick" executed successfully', job_name="email_tick", is_success=True),
            _entry(message='Running job "email_tick"', job_name="email_tick"),
            _entry(message='Job "email_tick" executed successfully', job_name="email_tick", is_success=True),
        ]
        jobs = aggregate_jobs(entries)
        email_job = next((j for j in jobs if j.name == "email_tick"), None)
        assert email_job is not None
        assert email_job.status == HealthStatus.HEALTHY
        assert email_job.total_errors == 0
        assert email_job.total_successes == 2

    def test_failing_job(self):
        entries = [
            _entry(message='Running job "sync_tick"', job_name="sync_tick"),
            _entry(
                level="ERROR",
                message='Job "sync_tick" raised an exception',
                job_name="sync_tick",
                is_error=True,
            ),
            _entry(message='Running job "sync_tick"', job_name="sync_tick"),
            _entry(
                level="ERROR",
                message='Job "sync_tick" raised an exception',
                job_name="sync_tick",
                is_error=True,
            ),
        ]
        jobs = aggregate_jobs(entries)
        sync_job = next((j for j in jobs if j.name == "sync_tick"), None)
        assert sync_job is not None
        assert sync_job.status == HealthStatus.FAILING
        assert sync_job.total_errors == 2

    def test_degraded_job(self):
        entries = [
            _entry(message='Running job "news_tick"', job_name="news_tick"),
            _entry(message='Job "news_tick" executed successfully', job_name="news_tick", is_success=True),
            _entry(message='Running job "news_tick"', job_name="news_tick"),
            _entry(message='Job "news_tick" executed successfully', job_name="news_tick", is_success=True),
            _entry(message='Running job "news_tick"', job_name="news_tick"),
            _entry(message='Job "news_tick" executed successfully', job_name="news_tick", is_success=True),
            _entry(message='Running job "news_tick"', job_name="news_tick"),
            _entry(
                level="ERROR",
                message='Job "news_tick" raised an exception',
                job_name="news_tick",
                is_error=True,
            ),
        ]
        jobs = aggregate_jobs(entries)
        news_job = next((j for j in jobs if j.name == "news_tick"), None)
        assert news_job is not None
        assert news_job.status == HealthStatus.DEGRADED

    def test_no_job_data(self):
        entries = [_entry(message="some random log line")]
        jobs = aggregate_jobs(entries)
        assert jobs == []

    def test_multiple_jobs(self):
        entries = [
            _entry(message='Running job "email_tick"', job_name="email_tick"),
            _entry(message='Job "email_tick" executed successfully', job_name="email_tick", is_success=True),
            _entry(message='Running job "sync_tick"', job_name="sync_tick"),
            _entry(level="ERROR", message='Job "sync_tick" raised an exception', job_name="sync_tick", is_error=True),
        ]
        jobs = aggregate_jobs(entries)
        assert len(jobs) == 2
        names = {j.name for j in jobs}
        assert "email_tick" in names
        assert "sync_tick" in names


class TestAggregateErrorPatterns:
    def test_single_pattern(self):
        entries = [
            _entry(level="ERROR", message="ValueError: invalid input", is_error=True),
            _entry(level="ERROR", message="ValueError: invalid input", is_error=True),
            _entry(level="ERROR", message="ValueError: invalid input", is_error=True),
        ]
        patterns = aggregate_error_patterns(entries)
        assert len(patterns) >= 1
        assert patterns[0].count == 3

    def test_no_errors(self):
        entries = [_entry(message="all good")]
        patterns = aggregate_error_patterns(entries)
        assert patterns == []

    def test_multiple_patterns(self):
        entries = [
            _entry(level="ERROR", message="ValueError: invalid input", is_error=True),
            _entry(level="ERROR", message="TypeError: expected str", is_error=True),
            _entry(level="ERROR", message="ValueError: invalid input", is_error=True),
        ]
        patterns = aggregate_error_patterns(entries)
        assert len(patterns) >= 2


class TestBuildSystemHealth:
    def test_with_default_logs(self):
        """Build from actual Jarmes logs if available."""
        health = build_system_health(max_lines=100)
        # Should not crash even if logs don't exist
        assert health is not None
        assert health.total_lines_parsed >= 0

    def test_with_nonexistent_path(self):
        health = build_system_health(log_paths=["/nonexistent/log.txt"])
        assert health.total_lines_parsed == 0
        assert health.overall_status == HealthStatus.UNKNOWN
