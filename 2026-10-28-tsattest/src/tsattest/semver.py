"""Minimal semantic-version parsing for what `tailscale version` actually prints.

Real output is not clean semver: the long version is
``1.102.3-t9329c3677-ga522f65e9``. Only the numeric triple participates in
comparison; the build suffix is carried for display and ignored for ordering.
"""

import re
from functools import total_ordering

_VERSION_RE = re.compile(r"^[vV]?(\d+)\.(\d+)\.(\d+)(?:[-+]([0-9A-Za-z.+-]+))?$")


@total_ordering
class Version(object):
    """A major.minor.patch triple with an optional, non-comparable build suffix."""

    __slots__ = ("major", "minor", "patch", "build")

    def __init__(self, major, minor, patch, build=""):
        self.major = int(major)
        self.minor = int(minor)
        self.patch = int(patch)
        self.build = build or ""

    def _triple(self):
        return (self.major, self.minor, self.patch)

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._triple() == other._triple()

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._triple() < other._triple()

    def __hash__(self):
        return hash(self._triple())

    def __str__(self):
        text = "%d.%d.%d" % self._triple()
        return text + ("-" + self.build if self.build else "")

    def __repr__(self):
        return "Version(%r)" % (str(self),)


def parse(text):
    """Parse one version token. Raises ValueError if it is not a version.

    Accepts surrounding whitespace and a leading ``v``; rejects anything that
    is not a three-part numeric version.
    """
    if not isinstance(text, str):
        raise ValueError("version must be a string, got %r" % (text,))
    match = _VERSION_RE.match(text.strip())
    if not match:
        raise ValueError("not a version: %r" % (text,))
    return Version(match.group(1), match.group(2), match.group(3), match.group(4) or "")


def first_line(text):
    """Return the first non-empty line of a command's stdout, or ''."""
    for line in (text or "").splitlines():
        if line.strip():
            return line.strip()
    return ""
