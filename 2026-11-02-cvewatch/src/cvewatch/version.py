"""Debian/dpkg version ordering, ported to the algorithm dpkg actually uses.

Why this exists: the difference between "5 ABI levels short" and "already fixed" is one
comparison, and the naive comparison gets it wrong on exactly the cases that matter
(``7.0.0-9.9`` > ``7.0.0-43.43`` as strings). Ubuntu kernel versions carry an ABI suffix
after the dash, so a string compare is not an acceptable substitute.
"""


def split_version(version):
    """Return ``(epoch, upstream, revision)`` the way dpkg parses a version string."""
    text = version.strip()
    epoch, sep, rest = text.partition(":")
    if not sep or not rest:
        epoch, rest = "0", text
    upstream, sep, revision = rest.rpartition("-")
    if not sep or not upstream:
        upstream, revision = rest, ""
    return epoch, upstream, revision


def _order(char):
    """Character weight in dpkg's ordering: '~' sorts before everything, letters before
    punctuation, end-of-string in between."""
    if char == "~":
        return -1
    if char.isdigit():
        return 0
    if char.isalpha():
        return ord(char)
    return ord(char) + 256


def _verrevcmp(left, right):
    """Alternating non-digit / digit comparison over an upstream or revision fragment.

    This mirrors dpkg's ``verrevcmp``: compare non-digit characters one at a time (a digit
    weighs 0, so it loses to any letter), then compare the digit run numerically with
    leading zeros ignored. End-of-string weighs 0.
    """
    i = j = 0
    len_left, len_right = len(left), len(right)
    while i < len_left or j < len_right:
        while ((i < len_left and not left[i].isdigit())
               or (j < len_right and not right[j].isdigit())):
            weight_a = _order(left[i]) if i < len_left else 0
            weight_b = _order(right[j]) if j < len_right else 0
            if weight_a != weight_b:
                return weight_a - weight_b
            i += 1
            j += 1
        while i < len_left and left[i] == "0":
            i += 1
        while j < len_right and right[j] == "0":
            j += 1
        start_a, start_b = i, j
        while i < len_left and left[i].isdigit():
            i += 1
        while j < len_right and right[j].isdigit():
            j += 1
        digits_a = left[start_a:i]
        digits_b = right[start_b:j]
        if len(digits_a) != len(digits_b):
            return len(digits_a) - len(digits_b)
        if digits_a != digits_b:
            return -1 if digits_a < digits_b else 1
    return 0


def compare(left, right):
    """Return -1, 0 or 1 for ``left`` older than / equal to / newer than ``right``."""
    epoch_a, upstream_a, revision_a = split_version(left)
    epoch_b, upstream_b, revision_b = split_version(right)
    try:
        diff = int(epoch_a) - int(epoch_b)
    except ValueError:
        diff = _verrevcmp(epoch_a, epoch_b)
    if diff:
        return -1 if diff < 0 else 1
    diff = _verrevcmp(upstream_a, upstream_b)
    if diff:
        return -1 if diff < 0 else 1
    diff = _verrevcmp(revision_a, revision_b)
    if diff:
        return -1 if diff < 0 else 1
    return 0


def is_newer_or_equal(candidate, baseline):
    """True when ``candidate`` is at or above ``baseline`` in dpkg order."""
    return compare(candidate, baseline) >= 0
