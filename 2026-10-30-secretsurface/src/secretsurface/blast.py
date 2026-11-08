"""Blast radius: what makes a sighting worse than a text match.

Each signal is measured, not inferred. The point is to rank the same finding
differently depending on where it sits -- key material in a `.env.bak` is a
different problem from key material in a `.env`, even with identical bytes.

Publication state is the one signal only git can answer. The previous version of
this module asked whether a `.git` directory existed above the file, which is true
for every file inside a repository regardless of whether it is committed, about to
be committed, or excluded -- a signal that is always true and therefore carries no
information. Locating the repository is now a precondition; the question is put to
git.
"""
import os
import subprocess
from pathlib import Path

_MAX_PARENT_DEPTH = 24
_GIT_TIMEOUT_SECS = 10

# The answers git can give about whether a file leaves this machine.
PUBLICATION_TRACKED = "git-tracked"
PUBLICATION_UNTRACKED_UNIGNORED = "git-untracked-unignored"
PUBLICATION_IGNORED = "git-ignored"
PUBLICATION_NO_WORKTREE = "no-git-worktree"
PUBLICATION_UNKNOWN = "git-unknown"

# Ordered most-exposed-first. `git-unknown` sits above `git-ignored` on purpose:
# a git we could not ask must never sort below one we proved excluded the file, or
# a git failure would read as safety.
PUBLICATION_ORDER = (
    PUBLICATION_TRACKED,
    PUBLICATION_UNTRACKED_UNIGNORED,
    PUBLICATION_UNKNOWN,
    PUBLICATION_NO_WORKTREE,
    PUBLICATION_IGNORED,
)

_state_cache: dict = {}
_git_call_count = 0


def _reset_caches() -> None:
    """Drop memoised state. Tests call this between fixtures."""
    global _git_call_count
    _state_cache.clear()
    _git_call_count = 0


def _git_calls() -> int:
    """How many git processes this module has spawned, for the cache test."""
    return _git_call_count


def _run_git(cwd, args):
    """Run one git query. None means git could not answer at all."""
    global _git_call_count
    try:
        _git_call_count += 1
        return subprocess.run(
            ["git", "-C", str(cwd)] + list(args),
            capture_output=True, text=True, timeout=_GIT_TIMEOUT_SECS,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _world_readable(path: Path) -> bool:
    try:
        return bool(path.stat().st_mode & 0o004)
    except OSError:
        return False


def _git_root(path: Path):
    """Nearest ancestor holding a `.git`, or None. A precondition, not a signal."""
    current = path.parent
    for _ in range(_MAX_PARENT_DEPTH):
        try:
            if (current / ".git").exists():
                return current
        except OSError:
            return None
        parent = current.parent
        if parent == current:
            return None
        current = parent
    return None


def publication_state(path) -> str:
    """One of PUBLICATION_ORDER's members, decided by git.

    Never returns `git-ignored` on a failure: "we could not prove it is published"
    and "we proved it is not published" are different facts, and only one is safe.
    """
    path = Path(path)
    key = str(path)
    cached = _state_cache.get(key)
    if cached is not None:
        return cached

    state = _resolve_publication(path)
    _state_cache[key] = state
    return state


def _resolve_publication(path: Path) -> str:
    try:
        if not path.exists():
            return PUBLICATION_UNKNOWN
    except OSError:
        return PUBLICATION_UNKNOWN

    root = _git_root(path)
    if root is None:
        # No repository anywhere above: git would not track this file even if
        # asked, so this is an answer, not a failure.
        return PUBLICATION_NO_WORKTREE

    tracked = _run_git(root, ("ls-files", "--error-unmatch", "--", str(path)))
    if tracked is None or tracked.returncode not in (0, 1):
        return PUBLICATION_UNKNOWN
    if tracked.returncode == 0:
        return PUBLICATION_TRACKED

    ignored = _run_git(root, ("check-ignore", "-q", "--", str(path)))
    if ignored is None or ignored.returncode not in (0, 1):
        return PUBLICATION_UNKNOWN
    if ignored.returncode == 0:
        return PUBLICATION_IGNORED
    return PUBLICATION_UNTRACKED_UNIGNORED


def publication_rank(signals) -> int:
    """Sort key: lower is more exposed. Absent signal ranks as unknown."""
    for signal in signals:
        if signal in PUBLICATION_ORDER:
            return PUBLICATION_ORDER.index(signal)
    return PUBLICATION_ORDER.index(PUBLICATION_UNKNOWN)


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
    signals.append(publication_state(path))
    if klass in ("env-backup", "backup-blob"):
        signals.append("superseded-key-may-still-validate")
    if klass == "log-leak":
        signals.append("copied-or-shipped")
    if klass == "committed-config":
        signals.append("committed-by-design")
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
