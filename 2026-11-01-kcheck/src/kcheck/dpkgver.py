"""Debian/Ubuntu version comparison -- the real dpkg algorithm, not a string compare.

This module exists because the naive comparison is actively dangerous here:
``"7.0.0-38" > "7.0.0-43.43"`` as strings, which would call a 5-patch-levels-short
kernel "patched". The other classic trap is ``"7.0.0-9"`` vs ``"7.0.0-10"``: string
compare says 9 > 10 and a vulnerable host is reported clean.

Ported from dpkg's ``lib/dpkg/version.c`` (``verrevcmp``/``order``), which is what
Ubuntu's own ``dpkg --compare-versions`` runs. No third-party code, no regex tricks --
the alternating non-digit / digit walk is reproduced literally because that is the
specification.
"""

import re

# Characters dpkg allows in an upstream version / revision.
_ALLOWED = re.compile(r"^[A-Za-z0-9.+~:-]+$")
_RELEASE_RE = re.compile(r"^(?P<base>\d+(?:\.\d+)*-\d+)(?:-(?P<flavour>[A-Za-z][A-Za-z0-9_]*))?$")


class VersionError(ValueError):
    """A string that is not a Debian version. Raised, never compared as if it were."""


def split_version(version):
    """``[epoch:]upstream[-revision]`` -> ``(epoch, upstream, revision)``."""
    text = (version or "").strip()
    if not text:
        raise VersionError("empty version string")
    if not _ALLOWED.match(text):
        raise VersionError("not a Debian version: %r" % version)

    epoch = 0
    if ":" in text:
        head, text = text.split(":", 1)
        if not head.isdigit():
            raise VersionError("non-numeric epoch in %r" % version)
        epoch = int(head)

    if "-" in text:
        upstream, revision = text.rsplit("-", 1)
    else:
        upstream, revision = text, ""
    if not upstream:
        raise VersionError("empty upstream version in %r" % version)
    return epoch, upstream, revision


def _order(char):
    """dpkg's collation: ``~`` before end-of-string, digits, letters, then punctuation."""
    if char == "~":
        return -1
    if char.isdigit():
        return 0
    if char.isalpha():
        return ord(char)
    return ord(char) + 256


def _verrevcmp(left, right):
    i = j = 0
    while i < len(left) or j < len(right):
        first_diff = 0
        # Non-digit run: compared character by character, end-of-string sorts as 0,
        # so "1.0~rc1" < "1.0" and "1.0a" < "1.0+".
        while (i < len(left) and not left[i].isdigit()) or (j < len(right) and not right[j].isdigit()):
            a = _order(left[i]) if i < len(left) else 0
            b = _order(right[j]) if j < len(right) else 0
            if a != b:
                return a - b
            i += 1
            j += 1
        # Digit run: leading zeros are insignificant, then numeric magnitude.
        while i < len(left) and left[i] == "0":
            i += 1
        while j < len(right) and right[j] == "0":
            j += 1
        while i < len(left) and j < len(right) and left[i].isdigit() and right[j].isdigit():
            if not first_diff:
                first_diff = ord(left[i]) - ord(right[j])
            i += 1
            j += 1
        if i < len(left) and left[i].isdigit():
            return 1
        if j < len(right) and right[j].isdigit():
            return -1
        if first_diff:
            return first_diff
    return 0


def compare(left, right):
    """Return -1, 0 or 1 for ``left`` <, ==, > ``right``. Raises on garbage."""
    l_epoch, l_up, l_rev = split_version(left)
    r_epoch, r_up, r_rev = split_version(right)
    if l_epoch != r_epoch:
        return -1 if l_epoch < r_epoch else 1
    result = _verrevcmp(l_up, r_up)
    if result:
        return -1 if result < 0 else 1
    result = _verrevcmp(l_rev, r_rev)
    if result:
        return -1 if result < 0 else 1
    return 0


def abi(version):
    """The ABI number at the head of the revision: ``7.0.0-38.38`` -> 38.

    None when the version has no ABI-shaped revision (e.g. upstream ``6.6.159``),
    because a gap between two different upstream trains is not a patch-level gap.
    """
    _, _, revision = split_version(version)
    digits = ""
    for char in revision:
        if not char.isdigit():
            break
        digits += char
    return int(digits) if digits else None


def abi_gap(installed, fixed):
    """How many ABI levels short the installed kernel is, or None if incomparable."""
    i_epoch, i_up, _ = split_version(installed)
    f_epoch, f_up, _ = split_version(fixed)
    if i_up != f_up or i_epoch != f_epoch:
        return None
    i_abi, f_abi = abi(installed), abi(fixed)
    if i_abi is None or f_abi is None:
        return None
    return f_abi - i_abi


def release_to_version(release):
    """``uname -r`` -> the comparable package version, best effort.

    ``7.0.0-38-generic`` -> ``7.0.0-38``. The flavour suffix (generic, lowlatency,
    azure, ...) is not part of the package version, and keeping it would make every
    comparison fail on an unparseable string. Used only as a fallback when the
    installed package version cannot be read -- the package DB is authoritative and is
    preferred.
    """
    text = (release or "").strip()
    match = _RELEASE_RE.match(text)
    if not match:
        return text
    return match.group("base")
