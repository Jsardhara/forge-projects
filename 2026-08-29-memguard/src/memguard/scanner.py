"""memguard.scanner -- orchestrate scanning of memory/prompt files."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Optional

from .models import Finding, ScanResult
from .rules import scan_text

# File suffixes/names treated as agent-context (memory, prompts, skills, notes).
_CONTEXT_GLOBS = (
    "*.md", "*.txt", "*.prompt", "*.system", "*.memory",
    "*.jsonl", "*.yaml", "*.yml", "*.json",
)
_TEXT_SUFFIXES = {".md", ".txt", ".markdown", ".prompt", ".system", ".memory",
                  ".yaml", ".yml", ".json", ".jsonl", ".rst", ".log"}


def _is_context_file(path: Path) -> bool:
    return path.suffix.lower() in _TEXT_SUFFIXES


def collect_files(paths: Iterable[str], recursive: bool = True) -> List[Path]:
    """Expand the given paths into a list of context files to scan.

    Recursively walks directories, skipping VCS/internal dirs.
    """
    out: List[Path] = []
    skip_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__",
                 ".hermes", "dist", "build", ".egg-info", ".tox", ".mypy_cache"}
    for raw in paths:
        p = Path(raw)
        if not p.exists():
            continue
        if p.is_file():
            if _is_context_file(p):
                out.append(p)
            continue
        if p.is_dir():
            if not recursive:
                try:
                    for child in p.iterdir():
                        if child.is_file() and _is_context_file(child):
                            out.append(child)
                except OSError:
                    pass
                continue
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                for fn in files:
                    fp = Path(root) / fn
                    if _is_context_file(fp):
                        out.append(fp)
    return out


def scan_paths(paths: Iterable[str],
               recursive: bool = True,
               encoding: str = "utf-8") -> List[ScanResult]:
    """Scan the given files/dirs, returning one ScanResult per file."""
    results: List[ScanResult] = []
    files = collect_files(paths, recursive=recursive)
    for fp in files:
        try:
            text = fp.read_text(encoding=encoding, errors="replace")
        except OSError as exc:
            results.append(ScanResult(path=str(fp), error=f"read error: {exc}"))
            continue
        findings = scan_text(text, str(fp))
        results.append(ScanResult(path=str(fp), findings=findings))
    return results


def aggregate_score(results: Iterable[ScanResult]) -> float:
    """Return the highest score across results (overall risk = worst file)."""
    return max((r.score() for r in results), default=0.0)


def aggregate_verdict(results: Iterable[ScanResult]):
    from .models import Verdict
    scores = {r.verdict().value for r in results}
    order = ["CLEAN", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    rank = {v: i for i, v in enumerate(order)}
    return Verdict(max((s for s in scores), key=lambda s: rank[s])) if scores else Verdict.CLEAN