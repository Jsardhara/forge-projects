"""Catalogs reference lyrics, screens an input lyric, and aggregates verdicts."""
from __future__ import annotations

import os
from typing import Dict, List, Optional

from .models import (
    SEVERITY_RANK,
    ReferenceMatch,
    ScreenReport,
    Severity,
    Verdict,
)
from .normalize import shingles, tokenize
from .screener import containment, intersect_size, jaccard, longest_common_run

# Longest contiguous common phrase (in tokens) at/beyond which we treat a chunk
# as verbatim "sampling" regardless of overall overlap.
MIN_PHRASE = 6
# Above these, a reference match is a hard FLAG.
FLAG_LONG_RUN = 16
FLAG_CONTAINMENT = 0.35
FLAG_JACCARD = 0.50
# Between MIN_PHRASE and FLAG levels is a REVIEW (human adjudication) band.
REVIEW_CONTAINMENT = 0.15
REVIEW_JACCARD = 0.25

_TEXT_EXTS = {"txt", "md", "lrc", "ly", "srt", ""}


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


class SongguardError(Exception):
    """Raised for unreadable input/reference content."""


def load_catalog(reference: str) -> Dict[str, str]:
    """Load a reference entry (file) or a directory of lyric files -> name->text."""
    refs: Dict[str, str] = {}
    if os.path.isdir(reference):
        for name in sorted(os.listdir(reference)):
            full = os.path.join(reference, name)
            if not os.path.isfile(full):
                continue
            ext = os.path.splitext(name)[1].lstrip(".").lower()
            if ext in _TEXT_EXTS:
                refs[name] = _read_text(full)
    elif os.path.isfile(reference):
        refs[os.path.basename(reference)] = _read_text(reference)
    else:
        raise SongguardError(f"reference not found: {reference}")
    return refs


def _severity(c: float, j: float, run: int) -> Severity:
    if run >= FLAG_LONG_RUN or c >= FLAG_CONTAINMENT or j >= FLAG_JACCARD:
        return Severity.FLAG
    if run >= MIN_PHRASE or c >= REVIEW_CONTAINMENT or j >= REVIEW_JACCARD:
        return Severity.REVIEW
    return Severity.PASS


def screen_text(input_text: str, refs: Dict[str, str]) -> ScreenReport:
    """Screen an input lyric string against a catalog of reference lyric texts."""
    in_tokens = tokenize(input_text)
    in_shingles = shingles(in_tokens)
    in_count = len(in_shingles)

    matches: List[ReferenceMatch] = []
    for name, ref_text in refs.items():
        ref_tokens = tokenize(ref_text)
        ref_shingles = shingles(ref_tokens)
        inter = intersect_size(in_shingles, ref_shingles)
        c = containment(in_count, inter)
        j = jaccard(inter, in_count, len(ref_shingles))
        run, phrase = longest_common_run(in_tokens, ref_tokens)
        matches.append(
            ReferenceMatch(
                ref_name=name,
                ref_path=name,
                containment=c,
                jaccard=j,
                longest_run=run,
                sampled_phrase=phrase,
                severity=_severity(c, j, run),
            )
        )

    if not matches:
        return ScreenReport(input_path="<string>", score=0, verdict=Verdict.CLEAR)

    # Per-reference risk = worst single signal magnitude. The longest common
    # phrase run is the strongest "sampling" signal, so it can dominate even
    # when overall overlap is diluted by unique surrounding verses.
    per_ref_risk = []
    for m in matches:
        run_risk = min(m.longest_run, 24) / 24.0
        per_ref_risk.append(max(m.containment, m.jaccard, run_risk))
    score = min(100, round(100 * max(per_ref_risk)))

    worst = max((m.severity for m in matches), key=lambda s: SEVERITY_RANK[s])
    verdict = {
        Severity.FLAG: Verdict.INFRINGE,
        Severity.REVIEW: Verdict.REVIEW,
        Severity.PASS: Verdict.CLEAR,
    }[worst]

    return ScreenReport(
        input_path="<string>", score=score, verdict=verdict, matches=matches
    )


def screen_file(input_path: str, reference: str) -> ScreenReport:
    """Screen a lyric file against a reference file or directory of lyric files."""
    if not os.path.isfile(input_path):
        raise SongguardError(f"input not found: {input_path}")
    input_text = _read_text(input_path)
    refs = load_catalog(reference)
    report = screen_text(input_text, refs)
    report.input_path = os.path.basename(input_path)
    return report