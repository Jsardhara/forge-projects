"""Version parsing and comparison.

Deliberately small and total: this tool compares a handful of shapes that really
appear on disk -- semver-ish runtime versions ("26.8.2"), four-part wheel versions
("1.2.1.0"), and Debian/RPM package versions ("1.2.0-3build1", "1.2.0-3.fc42").
Anything outside those shapes raises rather than guessing, because a guessed
version silently produces a confident wrong verdict.
"""

from __future__ import annotations

import re
from typing import Tuple

__all__ = ["VersionError", "parse", "base", "compare", "is_below"]


class VersionError(ValueError):
    """Raised when a version string is not in a shape this tool understands."""


_LEADING_V = re.compile(r"^[vV]")
_SPLIT = re.compile(r"[.+]")
_REVISION = re.compile(r"[-~].*$")
_LOCAL_SEGMENT = re.compile(r"\+.*$")


def _clean(text: str) -> str:
    if not isinstance(text, str):
        raise VersionError("version must be a string, got %r" % (text,))
    cleaned = _LEADING_V.sub("", text.strip())
    if not cleaned:
        raise VersionError("empty version string")
    return cleaned


def base(text: str) -> Tuple[int, ...]:
    """The upstream version core: no epoch/revision, no local build segment.

    "1.2.0-3build1" -> (1, 2, 0); "2.14.0+cu130" -> (2, 14, 0).
    """
    core = _REVISION.sub("", _LOCAL_SEGMENT.sub("", _clean(text)))
    return parse(core)


def parse(text: str) -> Tuple[int, ...]:
    """Parse the numeric part of a dotted version into an int tuple."""
    cleaned = _clean(text)
    parts = _SPLIT.split(cleaned)
    if not parts or parts[-1] == "":
        raise VersionError("trailing separator in version %r" % (text,))
    numbers = []
    for part in parts:
        if not part.isdigit():
            raise VersionError("non-numeric version component %r in %r" % (part, text))
        numbers.append(int(part))
    return tuple(numbers)


def _pad(left: Tuple[int, ...], right: Tuple[int, ...]):
    width = max(len(left), len(right))
    return (
        left + (0,) * (width - len(left)),
        right + (0,) * (width - len(right)),
    )


def compare(left: str, right: str) -> int:
    """-1 / 0 / 1. Numeric per component, missing components treated as zero."""
    a = tuple(int(p) for p in _numeric_or_raise(left))
    b = tuple(int(p) for p in _numeric_or_raise(right))
    a, b = _pad(a, b)
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def _numeric_or_raise(text: str) -> Tuple[int, ...]:
    """Like parse(), but tolerates a Debian-style revision on either side."""
    try:
        return base(text)
    except VersionError:
        return parse(text)


def is_below(version: str, target: str) -> bool:
    return compare(version, target) < 0
