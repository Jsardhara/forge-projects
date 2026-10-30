"""High-precision credential patterns.

Design rule: precision over recall. A scanner that cries wolf is uninstalled
within a week, so this table holds only shapes that are unambiguous in
practice. Every match is reduced to (pattern id, line, fingerprint, length) --
the value itself never leaves this module.
"""
import hashlib
import re
from typing import NamedTuple

# Tokens that mean "this is documentation, not a credential". Checked against
# the whole matched value, case-insensitively.
_PLACEHOLDER_WORDS = re.compile(
    r"redact|placeholder|example|dummy|sample|fake|your[_-]|insert|changeme"
    r"|replace|todo|xxxx|\.\.\.|\.\.\.",
    re.IGNORECASE,
)

# A value drawn from very few distinct characters carries almost no entropy.
_MIN_DISTINCT_CHARS = 4


class Pattern(NamedTuple):
    """A credential shape. `id` is what a report cites; never the value."""

    id: str
    regex: "re.Pattern[str]"
    description: str


class Match(NamedTuple):
    """A sighting. Deliberately cannot carry the secret (see tests)."""

    pattern_id: str
    line: int
    fingerprint: str
    value_len: int


def _p(pattern_id: str, pattern: str, description: str) -> Pattern:
    return Pattern(pattern_id, re.compile(pattern), description)


PATTERNS: tuple[Pattern, ...] = (
    _p("aws-access-key", r"\bAKIA[0-9A-Z]{16}\b",
       "AWS access key id (AKIA prefix + 16 upper/digits)"),
    _p("github-token", r"\bghp_[A-Za-z0-9]{36}\b",
       "GitHub personal access token (classic)"),
    _p("generic-sk-key", r"\bsk-[A-Za-z0-9_-]{20,}",
       "OpenAI/Anthropic-style secret key (sk- prefix)"),
    _p("slack-bot-token", r"\bxoxb-[0-9A-Za-z-]{10,}",
       "Slack bot token"),
    _p("google-api-key", r"\bAIza[0-9A-Za-z_-]{35}\b",
       "Google API key (AIza prefix + 35)"),
    _p("private-key-pem", r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----",
       "PEM private key header"),
)

def is_placeholder(value: str) -> bool:
    """True when the matched text is documentation or a redaction, not a key."""
    if _PLACEHOLDER_WORDS.search(value):
        return True
    if len(set(value)) < _MIN_DISTINCT_CHARS:
        return True
    return False


def fingerprint(value: str) -> str:
    """First 4 hex chars of sha256 -- enough to correlate, useless to reuse."""
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:4]


# Shapes that are only a credential when an actual payload follows them. A PEM
# header alone is how documentation writes it; a header plus base64 body is how
# a key looks. Without this, every skill doc mentioning the marker reports a
# finding -- which is how a scanner loses its audience.
_NEEDS_BODY = {"private-key-pem"}
_BODY = re.compile(r"[A-Za-z0-9+/=]{32,}")
_BODY_LOOKAHEAD = 2


def _has_body(lines: list, index: int) -> bool:
    for candidate in lines[index + 1:index + 1 + _BODY_LOOKAHEAD]:
        if _BODY.search(candidate):
            return True
    return False


def find_matches(text: str) -> list:
    """Scan text for credential shapes; drop placeholders.

    Returns Match objects ordered by line then by position, so reports are
    deterministic across runs.
    """
    lines = text.splitlines()
    found: list = []
    for index, line in enumerate(lines):
        line_no = index + 1
        hits: list = []
        for pattern in PATTERNS:
            if pattern.id in _NEEDS_BODY and not _has_body(lines, index):
                continue
            for hit in pattern.regex.finditer(line):
                value = hit.group(0)
                if is_placeholder(value):
                    continue
                hits.append((hit.start(), Match(
                    pattern_id=pattern.id,
                    line=line_no,
                    fingerprint=fingerprint(value),
                    value_len=len(value),
                )))
        hits.sort(key=lambda pair: pair[0])
        found.extend(match for _, match in hits)
    return found
