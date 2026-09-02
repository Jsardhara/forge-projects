"""Identity-asset detection and validation for idguard.

Zero dependencies. Designed so no regex uses escape sequences (no \\d, \\b, \\s)
so string content survives any content-layer mangling; character classes only.

DL formats are the classic (pre-Real-ID) NNA/published state formats. They are
representative, not authoritative: a raw number can match multiple states. We
report candidate states as HINTS, never as an identity claim. SSN validation is
authoritative (classic SSA area/group/serial rules).
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# US drivers'-license formats (classic, per-state). KEY -> compiled regex.
# Value is the list of candidate state abbreviations whose classic format
# matches the input. Encode only well-documented classic formats.
# ---------------------------------------------------------------------------
_STATE_DL_PATTERNS: "dict[str, re.Pattern]" = {
    "AL": re.compile(r"^[0-9]{8,9}$"),
    "AK": re.compile(r"^[0-9]{7}$"),
    "AZ": re.compile(r"^[0-9]{9}$"),
    "CA": re.compile(r"^([0-9]{9}|[0-9][A-Z][0-9]{7})$"),
    "CO": re.compile(r"^([0-9]{9}|[0-9]{4}[A-Z][0-9]{4})$"),
    "CT": re.compile(r"^[0-9]{9}$"),
    "FL": re.compile(r"^[A-Z][0-9]{12}$"),
    "GA": re.compile(r"^[0-9]{9}$"),
    "IL": re.compile(r"^([0-9]{12}|[A-Z][0-9]{11})$"),
    "MI": re.compile(r"^[A-Z][0-9]{12}$"),
    "NY": re.compile(r"^[A-Z][0-9]{8}$"),
    "OH": re.compile(r"^[A-Z][0-9]{7}$"),
    "PA": re.compile(r"^([0-9]{9}|[A-Z][0-9]{8})$"),
    "TX": re.compile(r"^([0-9]{9}|[0-9]{2}[A-Z][0-9]{6})$"),
    "VA": re.compile(r"^[0-9]{8,9}$"),
    "WA": re.compile(r"^[0-9]{9}$"),
}

# Generic US DL fallback (any state not encoded / unknown format).
_GENERIC_DL = re.compile(r"^[A-Z0-9]{7,17}$")

# Plain-text PII helpers (no escapes).
_EMAIL_RE = re.compile(r"^[^@ ]+@[^@ ]+[.][^@ ]+$")
_PHONE_RE = re.compile(r"^[(]?[+]?[0-9][0-9 ().-]{5,}[0-9]$")
_DOB_RE = re.compile(r"^[0-9]{4}[-/][0-9]{2}[-/][0-9]{2}$")  # ISO-ish
_DOB_RE2 = re.compile(r"^[0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{4}$")  # M/D/Y

# SSN "advertising" / known-invalid special cases.
_SSN_ADVERTISING = {"078051120", "219099999", "457555462"}
_SSN_ADS = set("123459999")


def validate_ssn(raw: str) -> Tuple[bool, str]:
    """Return (is_valid, reason). Accepts separators; validates classic SSA rules."""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) != 9:
        return False, "not 9 digits"
    if digits in _SSN_ADVERTISING:
        return False, "known invalid/advertising number"
    area = int(digits[0:3])
    group = int(digits[3:5])
    serial = int(digits[5:9])
    if area == 0:
        return False, "area 000 invalid"
    if area == 666:
        return False, "area 666 never issued"
    if area > 899:
        return False, "area 900+ never issued (reserved)"
    if group == 0:
        return False, "group 00 invalid"
    if serial == 0:
        return False, "serial 0000 invalid"
    if digits in _SSN_ADS:
        return False, "known invalid/advertising number"
    return True, digits


def looks_like_ssn(raw: str) -> bool:
    """True if 9 consecutive digits (masking spaces/dashes) are present."""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) != 9:
        return False
    # must be actual run of 9 digits, not a longer number
    return len(raw.translate({ord(c): None for c in " -"})) == 9


def detect_dl(raw: str) -> List[str]:
    """Return candidate state codes whose classic format matches, else [] for a
    generic-US-number match. Never an identity claim; purely a hint."""
    val = raw.strip()
    if not val:
        return []
    matches = [code for code, rx in _STATE_DL_PATTERNS.items() if rx.fullmatch(val)]
    if matches:
        return matches
    if _GENERIC_DL.fullmatch(val):
        return ["generic"]
    return []


def detect_email(raw: str) -> bool:
    return bool(_EMAIL_RE.match(raw.strip()))


def detect_phone(raw: str) -> bool:
    return bool(_PHONE_RE.fullmatch(raw.strip()))


def detect_dob(raw: str) -> bool:
    v = raw.strip()
    return bool(_DOB_RE.fullmatch(v) or _DOB_RE2.fullmatch(v))


def normalize_ssn(raw: str) -> Optional[str]:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 9:
        return digits
    return None