"""Tests for healthpulse.parser module."""

import datetime as dt
import tempfile
import os

import pytest

from healthpulse.parser import (
    LOG_PATTERN,
    parse_line,
    parse_file,
    parse_timestamp,
    JOB_RUNNING_PATTERN,
    JOB_ERROR_PATTERN,
    JOB_SUCCESS_PATTERN,
)


class TestParseTimestamp:
    def test_valid_timestamp(self):
        ts = parse_timestamp("2026-05-04 13:25:53,450")
        assert ts == dt.datetime(2026, 5, 4, 13, 25, 53, 450000)

    def test_invalid_timestamp(self):
        ts = parse_timestamp("not-a-timestamp")
        assert ts is None

    def test_empty_string(self):
        ts = parse_timestamp("")
        assert ts is None


class TestParseLine:
    def test_info_line(self):
        line = "2026-05-04 13:25:53,450 INFO jarvis.subsystems.registry: tempo: live mode"
        entry = parse_line(line)
        assert entry.level == "INFO"
        assert entry.source == "jarvis.subsystems.registry"
        assert entry.message == "tempo: live mode"
        assert entry.is_error is False
        assert entry.is_success is False

    def test_error_line(self):
        line = '2026-05-04 13:26:27,484 ERROR apscheduler.executors.default: Job "sync_tick" raised an exception'
        entry = parse_line(line)
        assert entry.level == "ERROR"
        assert entry.is_error is True
        assert entry.job_name == "sync_tick"

    def test_success_line(self):
        line = '2026-05-04 13:26:57,324 INFO apscheduler.executors.default: Job "heartbeat_tick" executed successfully'
        entry = parse_line(line)
        assert entry.is_success is True
        assert entry.job_name == "heartbeat_tick"

    def test_running_line(self):
        line = '2026-05-04 13:26:27,198 INFO apscheduler.executors.default: Running job "sync_tick (trigger: interval[0:00:30]"'
        entry = parse_line(line)
        # Job name should be cleaned (schedule details stripped)
        assert entry.job_name == "sync_tick"

    def test_empty_line(self):
        entry = parse_line("")
        assert entry.message == ""

    def test_garbage_line(self):
        entry = parse_line("this is not a log line at all")
        assert entry.raw == "this is not a log line at all"

    def test_warning_line(self):
        line = "2026-05-04 13:25:57,174 WARNING apscheduler.scheduler: Adding job tentatively"
        entry = parse_line(line)
        assert entry.level == "WARNING"
        assert entry.is_error is False


class TestParseFile:
    def test_parse_temp_file(self):
        content = """2026-05-04 13:25:53,450 INFO jarvis.subsystems.registry: tempo: live mode
2026-05-04 13:26:27,484 ERROR apscheduler.executors.default: Job "sync_tick" raised an exception
2026-05-04 13:26:57,324 INFO apscheduler.executors.default: Job "heartbeat_tick" executed successfully
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write(content)
            f.flush()
            path = f.name

        try:
            entries = parse_file(path)
            assert len(entries) == 3
            assert entries[0].level == "INFO"
            assert entries[1].level == "ERROR"
            assert entries[2].is_success is True
        finally:
            os.unlink(path)

    def test_nonexistent_file(self):
        entries = parse_file("/nonexistent/path/sentinel.log")
        assert entries == []

    def test_max_lines_from_end(self):
        lines = []
        for i in range(100):
            lines.append(f"2026-05-04 13:25:{i:02d},000 INFO test.source: message {i}")
        content = "\n".join(lines) + "\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write(content)
            f.flush()
            path = f.name

        try:
            entries = parse_file(path, max_lines=10, from_end=True)
            assert len(entries) == 10
            # Should be the LAST 10 lines
            assert "message 99" in entries[-1].message
        finally:
            os.unlink(path)

    def test_max_lines_from_start(self):
        lines = []
        for i in range(100):
            lines.append(f"2026-05-04 13:25:{i:02d},000 INFO test.source: message {i}")
        content = "\n".join(lines) + "\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write(content)
            f.flush()
            path = f.name

        try:
            entries = parse_file(path, max_lines=10, from_end=False)
            assert len(entries) == 10
            assert "message 0" in entries[0].message
        finally:
            os.unlink(path)


class TestJobPatterns:
    def test_job_running(self):
        msg = 'Running job "email_tick (trigger: interval[0:05:00]"'
        m = JOB_RUNNING_PATTERN.search(msg)
        assert m is not None
        assert "email_tick" in m.group("job_name")

    def test_job_error(self):
        msg = 'Job "sync_tick" raised an exception'
        m = JOB_ERROR_PATTERN.search(msg)
        assert m is not None
        assert m.group("job_name") == "sync_tick"

    def test_job_success(self):
        msg = 'Job "heartbeat_tick" executed successfully'
        m = JOB_SUCCESS_PATTERN.search(msg)
        assert m is not None
        assert m.group("job_name") == "heartbeat_tick"
