"""Text normalization and shingle construction for lyric comparison."""
from __future__ import annotations

import re
from typing import Iterable, List, Set, Tuple

# Only converted to lowercase; apostrophes preserved so "don't" stays one token.
_TOKEN_RE = re.compile(r"[a-z0-9']+")

# Common English function words. Shingles that consist entirely of these are
# dropped so that coincidence windows like ("and", "the") never produce a false
# similarity signal. The set is intentionally small and conservative.
STOPWORDS: frozenset = frozenset(
    """
    the a an and or but nor for with without at to from by on of in into out
    over under again then once here there when about who whom this that these
    those i me my mine we us our you your yours he him his she her hers it its
    they them their theirs am is are was were be been being do does did have has
    had having will would shall should can could may might must not no nor of
    what which while as up down off on so if after before above below too as
    where why how all any both each few more most other some such only own same
    s t can't won't don't i'm we're they're it's you're i've we've i'll we'll
    """.split()
)


def tokenize(text: str) -> List[str]:
    """Lowercase, drop punctuation/whitespace, keep letters/digits/apostrophes."""
    return _TOKEN_RE.findall(text.lower())


def is_significant(token: str) -> bool:
    return token not in STOPWORDS


def shingles(
    tokens: Iterable[str],
    n: int = 2,
    min_significant: int = 1,
) -> Set[Tuple[str, ...]]:
    """Build n-gram token shingles, dropping windows with too few content words."""
    toks = list(tokens)
    out: Set[Tuple[str, ...]] = set()
    if n < 1 or len(toks) < n:
        return out
    for i in range(len(toks) - n + 1):
        window = tuple(toks[i : i + n])
        significant = sum(1 for t in window if is_significant(t))
        if significant >= min_significant:
            out.add(window)
    return out