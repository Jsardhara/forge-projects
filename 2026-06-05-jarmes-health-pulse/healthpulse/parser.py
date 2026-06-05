"""Log file parser — reads and parses Jarmes log files."""

from __future__ import annotations

import datetime as dt
import os
import re
from pathlib import Path
from typing import Optional

from healthpulse.models import LogEntry

# APScheduler log format:
# 2026-05-04 13:25:53,450 INFO jarvis.subsystems.registry: tempo: live mode
LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s+"
    r"(?P<level>INFO|WARNING|ERROR|DEBUG|CRITICAL)\s+"
    r"(?P<source>[^:]+):\s+"
    r"(?P<message>.+)$"
)

# Job execution patterns
JOB_RUNNING_PATTERN = re.compile(
    r'Running job "(?P<job_name>[^"]+)"'
)
JOB_ERROR_PATTERN = re.compile(
    r'Job "(?P<job_name>[^"]+)" raised an exception'
)
JOB_SUCCESS_PATTERN = re.compile(
    r'Job "(?P<job_name>[^"]+)" executed successfully'
)


def _clean_job_name(raw_name: str) -> str:
    """Extract the actual job name from a log line job reference.

    Running job lines include schedule details:
        'sync_tick (trigger: interval[0:00:30], next run at: ...)'
    Error/success lines include just the name:
        'sync_tick'
    This function strips the schedule suffix.
    """
    # Take only the part before ' (' if present
    idx = raw_name.find(" (")
    if idx > 0:
        return raw_name[:idx]
    return raw_name

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S,%f"


def parse_timestamp(ts_str: str) -> Optional[dt.datetime]:
    """Parse a log timestamp string."""
    try:
        # Handle comma-separated milliseconds
        return dt.datetime.strptime(ts_str, TIMESTAMP_FORMAT)
    except ValueError:
        return None


def parse_line(line: str) -> LogEntry:
    """Parse a single log line into a LogEntry."""
    line = line.strip()
    if not line:
        return LogEntry(raw=line)

    m = LOG_PATTERN.match(line)
    if not m:
        return LogEntry(raw=line, message=line)

    ts = parse_timestamp(m.group("timestamp"))
    level = m.group("level")
    source = m.group("source")
    message = m.group("message")

    entry = LogEntry(
        timestamp=ts,
        level=level,
        source=source,
        message=message,
        raw=line,
        is_error=(level == "ERROR"),
    )

    # Extract job name from job-related messages
    for pattern in (JOB_RUNNING_PATTERN, JOB_ERROR_PATTERN, JOB_SUCCESS_PATTERN):
        jm = pattern.search(message)
        if jm:
            entry.job_name = _clean_job_name(jm.group("job_name"))
            break
            break

    if JOB_SUCCESS_PATTERN.search(message):
        entry.is_success = True

    return entry


def parse_file(
    path: str | Path,
    max_lines: int = 5000,
    from_end: bool = True,
) -> list[LogEntry]:
    """Parse a log file, returning a list of LogEntry objects.

    Args:
        path: Path to the log file.
        max_lines: Maximum lines to read (from end if from_end=True).
        from_end: If True, read last N lines instead of first N.
    """
    path = Path(path)
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except (IOError, OSError):
        return []

    if from_end and len(lines) > max_lines:
        lines = lines[-max_lines:]
    elif not from_end and len(lines) > max_lines:
        lines = lines[:max_lines]

    entries = []
    current_tb = None
    tb_lines: list[str] = []

    for line in lines:
        entry = parse_line(line)
        entries.append(entry)

        # Collect traceback lines after ERROR entries
        if entry.is_error:
            current_tb = entry
            tb_lines = []
        elif current_tb is not None:
            stripped = line.strip()
            if stripped.startswith("File ") or stripped.startswith("Traceback") or \
               stripped.startswith("  File ") or (stripped and not stripped[0].isalnum() and not stripped.startswith("20")):
                tb_lines.append(stripped)
            else:
                if tb_lines:
                    current_tb.traceback = "\n".join(tb_lines)
                current_tb = None
                tb_lines = []

    # Handle traceback at end of file
    if current_tb is not None and tb_lines:
        current_tb.traceback = "\n".join(tb_lines)

    return entries


def get_default_log_paths() -> list[Path]:
    """Return default Jarmes log file paths that exist."""
    base = Path(r"C:\Users\jyot2\jarvis\state")
    candidates = [
        base / "sentinel.log",
        base / "jarvis_api.log",
        base / "uvicorn.log",
    ]
    return [p for p in candidates if p.exists()]
