"""Classification: which KIND of store does a hit live in?

`grep .env` answers "is it in .env". This module answers "where is it", which
is a different question with a different answer set. `unknown` is a first-class
result: an unclassified hit is indistinguishable from a live one until someone
reads it, so it must never be bucketed as safe.
"""
from pathlib import PurePosixPath

# Ordered most-specific-first. Every class a report can emit.
CLASSES = ("env", "env-backup", "log-leak", "backup-blob", "doc-fixture", "unknown")

_ENV_BACKUP_TOKENS = {"bak", "old", "orig", "save", "swp", "bk", "backup"}
_ENV_DOC_TOKENS = {"example", "sample", "template", "dist"}
_BACKUP_DIRS = {"backups", "backup", ".curator_backups", "snapshots", "archive"}
_LOG_SUFFIXES = (".log", ".jsonl", ".ndjson")
_DOC_SUFFIXES = (".md", ".rst", ".adoc", ".txt")
_DOC_DIRS = {"skills", "docs", "doc", "tests", "test"}


def _parts(path: str) -> tuple:
    return PurePosixPath(str(path).replace("\\", "/")).parts


def _classify_env(name: str) -> str | None:
    """`.env`, `.env.local` are live; `.env.bak.*` is a superseded key."""
    if name == ".env":
        return "env"
    if not name.startswith(".env."):
        return None
    remainder = name[len(".env."):]
    tokens = set(remainder.lower().replace("-", ".").split("."))
    if tokens & _ENV_DOC_TOKENS:
        return "doc-fixture"
    if tokens & _ENV_BACKUP_TOKENS:
        return "env-backup"
    return "env"


def _is_log_leak(name: str, parts: tuple) -> bool:
    if name.endswith(_LOG_SUFFIXES):
        return True
    lowered = name.lower()
    return "activity" in lowered or lowered.endswith("_log") or lowered == "log"


def _is_backup_blob(name: str, parts: tuple) -> bool:
    if {p.lower() for p in parts} & _BACKUP_DIRS:
        return True
    if name.endswith("~") or name.endswith((".bak", ".old", ".orig")) or ".bak." in name:
        return True
    return any(part.lower() in _BACKUP_DIRS for part in parts[:-1])


def _is_doc_fixture(name: str, parts: tuple) -> bool:
    if {p.lower() for p in parts[:-1]} & _DOC_DIRS:
        return True
    if name.endswith(_DOC_SUFFIXES):
        return True
    return name.startswith("test_") or name.endswith("_test.py")


def classify_path(path: str) -> str:
    """Return one of CLASSES for a filesystem path. Never guesses 'safe'."""
    parts = _parts(path)
    name = parts[-1] if parts else ""

    env_kind = _classify_env(name)
    if env_kind is not None:
        return env_kind
    if _is_log_leak(name, parts):
        return "log-leak"
    if _is_backup_blob(name, parts):
        return "backup-blob"
    if _is_doc_fixture(name, parts):
        return "doc-fixture"
    return "unknown"
