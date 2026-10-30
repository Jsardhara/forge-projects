"""Blast radius: what makes a sighting worse than a text match.

Each signal is measured, not inferred. The point is to rank the same finding
differently depending on where it sits -- key material in a `.env.bak` is a
different problem from key material in a `.env`, even with identical bytes.
"""
import os
from pathlib import Path

_MAX_PARENT_DEPTH = 24


def _world_readable(path: Path) -> bool:
    try:
        return bool(path.stat().st_mode & 0o004)
    except OSError:
        return False


def _in_git_worktree(path: Path) -> bool:
    """True when a .git exists above the file -- it can be committed as-is."""
    current = path.parent
    for _ in range(_MAX_PARENT_DEPTH):
        try:
            if (current / ".git").exists():
                return True
        except OSError:
            return False
        parent = current.parent
        if parent == current:
            return False
        current = parent
    return False


def blast_signals(path, klass: str) -> tuple:
    """Measured risk signals for one finding. Empty tuple when unmeasurable."""
    path = Path(path)
    try:
        path.stat()
    except OSError:
        return ()
    signals: list = []
    if _world_readable(path):
        signals.append("world-readable")
    if _in_git_worktree(path):
        signals.append("in-git-worktree")
    if klass in ("env-backup", "backup-blob"):
        signals.append("superseded-key-may-still-validate")
    if klass == "log-leak":
        signals.append("copied-or-shipped")
    if klass == "unknown":
        signals.append("unclassified-store")
    return tuple(signals)


def summarise_by_root(findings, roots) -> dict:
    """Per-root totals and class breakdown, so one bad profile is visible."""
    root_keys = [str(root) for root in roots]
    summary = {key: {"total": 0, "classes": {}} for key in root_keys}
    for finding in findings:
        owner = _owner(finding.path, root_keys)
        if owner is None:
            continue
        summary[owner]["total"] += 1
        classes = summary[owner]["classes"]
        classes[finding.klass] = classes.get(finding.klass, 0) + 1
    return summary


def _owner(path: str, root_keys: list):
    """Longest root that prefixes the path, so nested roots win."""
    best = None
    for key in root_keys:
        if path == key or path.startswith(key.rstrip("/") + os.sep):
            if best is None or len(key) > len(best):
                best = key
    return best
