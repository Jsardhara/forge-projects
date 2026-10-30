"""Filesystem walk.

Two deliberate behaviours:

1. Dot-directories are NOT skipped. The measured leak on this host lives inside
   `.curator_backups/`, so a walker that hides dotdirs is a walker that reports
   clean while the key sits there.
2. Everything the walker does not read is reported with a reason. A skip that
   is not counted is a silent hole, and silent holes are how a scanner ends up
   green on a host that is not.
"""
import fnmatch
import os
from pathlib import Path

DEFAULT_MAX_BYTES = 4_000_000
_BINARY_PROBE = 8192

# Directories that are never scanned for working-surface key material. Each is
# recorded in the skip list so the report can say what was not looked at.
_SKIP_DIRS = {
    ".git": "vcs-internal: commit history is out of scope (use a history scanner)",
    "__pycache__": "cache: compiled bytecode",
    "node_modules": "vendor: dependency tree",
    ".venv": "vendor: virtualenv",
}

# Control files carry no key material of their own.
_SKIP_FILES = {".gitignore": "control-file"}


class _IgnoreRules:
    """Minimal .gitignore: globs, dir rules, negation, last-match-wins."""

    def __init__(self) -> None:
        self._cache: dict = {}

    def _rules_for(self, directory: Path) -> list:
        key = str(directory)
        if key not in self._cache:
            rules = []
            path = directory / ".gitignore"
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                lines = []
            for raw in lines:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                negate = line.startswith("!")
                if negate:
                    line = line[1:]
                rules.append((line.rstrip("/"), negate, line.endswith("/")))
            self._cache[key] = rules
        return self._cache[key]

    def ignored(self, path: Path, root: Path) -> bool:
        """True when the last matching rule (outermost to innermost) ignores it."""
        verdict = False
        chain = [root]
        try:
            relative_parent = path.parent.relative_to(root)
            current = root
            for part in relative_parent.parts:
                current = current / part
                chain.append(current)
        except ValueError:
            return False
        for directory in chain:
            try:
                rel = path.relative_to(directory).as_posix()
            except ValueError:
                continue
            for pattern, negate, dir_only in self._rules_for(directory):
                if _rule_matches(pattern, rel, dir_only):
                    verdict = not negate
        return verdict


def _rule_matches(pattern: str, rel: str, dir_only: bool) -> bool:
    if "/" in pattern.strip("/"):
        target = pattern.strip("/")
        return fnmatch.fnmatch(rel, target) or fnmatch.fnmatch(rel, target + "/*")
    if dir_only:
        ancestors = rel.split("/")[:-1]
        return any(fnmatch.fnmatch(part, pattern) for part in ancestors)
    return fnmatch.fnmatch(rel.split("/")[-1], pattern)


def _is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return b"\x00" in handle.read(_BINARY_PROBE)
    except OSError:
        return True


def read_text(path: Path):
    """Read a file as text, tolerating bad bytes. None when unreadable."""
    try:
        return path.read_bytes().decode("utf-8", "replace")
    except OSError:
        return None


def _walk_root(root: Path, max_bytes: int, ignore: _IgnoreRules) -> tuple:
    files: list = []
    skipped: list = []
    if not root.exists():
        return files, [(str(root), "root-missing: path does not exist")]
    if not root.is_dir():
        return files, [(str(root), "root-not-a-directory")]

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        here = Path(dirpath)
        keep = []
        for name in sorted(dirnames):
            reason = _SKIP_DIRS.get(name)
            if reason:
                skipped.append((str(here / name), reason))
            else:
                keep.append(name)
        dirnames[:] = keep

        for name in sorted(filenames):
            path = here / name
            if name in _SKIP_FILES:
                skipped.append((str(path), _SKIP_FILES[name]))
                continue
            if ignore.ignored(path, root):
                skipped.append((str(path), "gitignore"))
                continue
            try:
                size = path.stat().st_size
            except OSError:
                skipped.append((str(path), "unreadable: stat failed"))
                continue
            if size > max_bytes:
                skipped.append((str(path), "size: %d bytes over limit" % size))
                continue
            if _is_binary(path):
                skipped.append((str(path), "binary: NUL byte in first 8KB"))
                continue
            files.append(path)
    return files, skipped


def scan_tree(roots, max_bytes: int = DEFAULT_MAX_BYTES) -> tuple:
    """Walk roots. Returns (sorted readable files, sorted skip records)."""
    ignore = _IgnoreRules()
    files: list = []
    skipped: list = []
    for root in roots:
        found, holes = _walk_root(Path(root), max_bytes, ignore)
        files.extend(found)
        skipped.extend(holes)
    files.sort(key=str)
    skipped.sort(key=lambda pair: pair[0])
    return files, skipped
