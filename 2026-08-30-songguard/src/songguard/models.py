"""Data models for songguard screen results."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import List, Optional


class Severity(enum.Enum):
    """Per-reference-match risk level."""

    PASS = "PASS"
    REVIEW = "REVIEW"
    FLAG = "FLAG"


class Verdict(enum.Enum):
    """Aggregate screen verdict (severity-dominant across references)."""

    CLEAR = "CLEAR"
    REVIEW = "REVIEW"
    INFRINGE = "INFRINGE"


@dataclass
class ReferenceMatch:
    """Similarity of the input lyric against one reference catalog entry."""

    ref_name: str
    ref_path: str
    containment: float  # fraction of input shingles present in the reference (0-1)
    jaccard: float      # intersection/union of shingle sets (0-1)
    longest_run: int    # longest contiguous common word run (tokens)
    sampled_phrase: str  # the verbatim phrase behind longest_run ("" if none)
    severity: Severity


@dataclass
class ScreenReport:
    """Result of screening one input lyric against a reference set."""

    input_path: str
    score: int  # 0-100 weighted infringement magnitude
    verdict: Verdict
    matches: List[ReferenceMatch] = field(default_factory=list)

    def flag_count(self) -> int:
        return sum(1 for m in self.matches if m.severity == Severity.FLAG)

    def review_count(self) -> int:
        return sum(1 for m in self.matches if m.severity == Severity.REVIEW)


# Ordered severity rank used for the severity-dominant aggregate verdict.
SEVERITY_RANK = {Severity.PASS: 0, Severity.REVIEW: 1, Severity.FLAG: 2}