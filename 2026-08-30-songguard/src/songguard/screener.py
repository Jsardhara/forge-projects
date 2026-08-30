"""Similarity primitives: containment, Jaccard, and longest common phrase run."""
from __future__ import annotations

from typing import List, Sequence, Tuple


def longest_common_run(a: List[str], b: List[str]) -> Tuple[int, str]:
    """Return (max length, phrase) of the longest contiguous token run shared by a and b.

    Uses a classic O(n*m) dynamic-programming sweep over token equality. This models
    note-for-note "sampling" where a contiguous chunk of the original is reused.
    """
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return 0, ""
    prev = [0] * (m + 1)
    best = 0
    best_end_a = -1
    for i in range(n - 1, -1, -1):
        cur = [0] * (m + 1)
        ai = a[i]
        for j in range(m - 1, -1, -1):
            if ai == b[j]:
                cur[j] = prev[j + 1] + 1
                if cur[j] > best:
                    best = cur[j]
                    best_end_a = i
        prev = cur
    if best == 0:
        return 0, ""
    return best, " ".join(a[best_end_a : best_end_a + best])


def containment(ia: int, ib: int) -> float:
    """Fraction of the input shingle set present in the reference."""
    if ia == 0:
        return 0.0
    return round(float(ib) / float(ia), 4)


def jaccard(intersection: int, a: int, b: int) -> float:
    """Jaccard similarity over two shingle sets (both non-empty)."""
    union = a + b - intersection
    if union == 0:
        return 0.0
    return round(float(intersection) / float(union), 4)


def intersect_size(a: set, b: set) -> int:
    return len(a & b)