"""JSONL file readers with error resilience."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .models import BuildRun, ForgeRunEntry


def _read_jsonl(
    path: str | Path,
    skip_errors: bool = True,
) -> tuple[list[dict], int, int]:
    """Read a JSONL file, returning (valid_lines, total_lines, error_count).
    
    Args:
        path: Path to the JSONL file.
        skip_errors: If True, skip malformed lines. If False, raise on first error.
    
    Returns:
        Tuple of (list of parsed dicts, total lines read, number of errors).
    """
    p = Path(path)
    if not p.exists():
        return [], 0, 0

    results: list[dict] = []
    total = 0
    errors = 0

    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                errors += 1
                if not skip_errors:
                    raise

    return results, total, errors


def read_build_runs(
    path: str | Path = r"C:\Users\jyot2\jarvis\state\daily_projects.jsonl",
    skip_errors: bool = True,
) -> tuple[list[BuildRun], int, int]:
    """Read build runs from daily_projects.jsonl.
    
    Returns:
        Tuple of (list of BuildRun, total lines, error count).
    """
    records, total, errs = _read_jsonl(path, skip_errors)
    runs: list[BuildRun] = []
    for rec in records:
        try:
            runs.append(BuildRun.from_json(rec))
        except (ValueError, TypeError, KeyError):
            errs += 1
    return runs, total, errs


def read_forge_runs(
    path: str | Path = r"C:\Users\jyot2\jarvis\state\forge_runs.jsonl",
    skip_errors: bool = True,
) -> tuple[list[ForgeRunEntry], int, int]:
    """Read forge run entries from forge_runs.jsonl.
    
    Returns:
        Tuple of (list of ForgeRunEntry, total lines, error count).
    """
    records, total, errs = _read_jsonl(path, skip_errors)
    entries: list[ForgeRunEntry] = []
    for rec in records:
        try:
            entries.append(ForgeRunEntry.from_json(rec))
        except (ValueError, TypeError, KeyError):
            errs += 1
    return entries, total, errs


def read_cost_log(
    path: str | Path = r"C:\Users\jyot2\jarvis\state\cost_log.jsonl",
    skip_errors: bool = True,
) -> tuple[list[dict], int, int]:
    """Read raw cost log entries from cost_log.jsonl.
    
    Returns:
        Tuple of (list of dicts, total lines, error count).
    """
    return _read_jsonl(path, skip_errors)
