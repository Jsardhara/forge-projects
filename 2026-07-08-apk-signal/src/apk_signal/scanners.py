"""Scanners that extract signals from raw APK entry bytes.

Each scanner takes a decoded text blob (the entry's bytes decoded as latin-1,
which is lossless for byte->codepoint and safe for regex over ASCII substrings)
plus the entry name, and returns a list of Signal objects.

No external dependencies. Negation filtering prevents false positives on
innocent mentions such as "this app does not steal credentials".
"""

from __future__ import annotations

import re
from typing import List

from .models import Severity, Signal, SignalType

# --- Compiled patterns -------------------------------------------------------

_URL_RE = re.compile(
    r"""(?i)\bhttps?://[^\s"'<>(){}\[\]]{4,}""",
)
# Bare domain like evil-c2.example.com (requires a dot + tld-ish tail)
_DOMAIN_RE = re.compile(
    r"""(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}\b""",
)
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# Hardcoded secret patterns (high-signal strings only).
_SECRET_PATTERNS = [
    ("AWS Access Key ID", re.compile(r"AKIA[0-9A-Z]{16}"), Severity.CRITICAL, 25),
    ("Google API Key", re.compile(r"AIza[0-9A-Za-z_\-]{35}"), Severity.CRITICAL, 22),
    ("Slack Token", re.compile(r"xox[baprs]-[0-9A-Za-z\-]{10,}"), Severity.CRITICAL, 22),
    ("Stripe Secret Key", re.compile(r"sk_live_[0-9a-zA-Z]{16,}"), Severity.CRITICAL, 25),
    ("Telegram Bot Token", re.compile(r"\b\d{8,10}:[0-9A-Za-z_\-]{30,}\b"), Severity.HIGH, 18),
    ("Generic API Key assignment", re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{12,}['\"]"), Severity.HIGH, 12),
    ("PEM Private Key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PKCS8 )?PRIVATE KEY-----"), Severity.CRITICAL, 28),
    ("JWT", re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"), Severity.HIGH, 12),
    ("Google OAuth Client Secret", re.compile(r"[0-9]+-[0-9A-Za-z_\-]{24}\.apps\.googleusercontent\.com"), Severity.MEDIUM, 10),
]

# Suspicious capability keyword groups. Each maps to a severity and score.
_CAPABILITY_KEYWORDS = [
    ("Accessibility service abuse", re.compile(r"accessibilityservice|android\.accessibility", re.I), Severity.HIGH, 15),
    ("Overlay / screen capture", re.compile(r"system_alert_window|overlay|screencapture|media_projection", re.I), Severity.HIGH, 12),
    ("SMS interception", re.compile(r"read_sms|receive_sms|sms_retriever|intercept.*sms", re.I), Severity.HIGH, 14),
    ("Call / contact exfiltration", re.compile(r"read_contacts|read_call_log|read_phone_state|read_phone_numbers", re.I), Severity.MEDIUM, 10),
    ("Credential / password theft", re.compile(r"steal.*(password|credential)|keylog|grab.*(password|credential)|phish", re.I), Severity.CRITICAL, 20),
    ("OTP / 2FA theft", re.compile(r"\botp\b|2fa|authenticator|one.?time.?code|verification.?code", re.I), Severity.HIGH, 14),
    ("Crypto-wallet targeting", re.compile(r"wallet|metamask|trustwallet|binance|seed.?phrase|recovery.?phrase", re.I), Severity.HIGH, 14),
    ("Ransomware / lock screen", re.compile(r"ransom|lockdevice|lock_screen|encrypt.*files|device.*admin", re.I), Severity.CRITICAL, 18),
    ("Background / persistence", re.compile(r"boot_completed|foreground_service|wake_lock|persistent", re.I), Severity.LOW, 4),
    ("Root / hide", re.compile(r"su\b|superuser|hide.?app|root.*beer|magisk", re.I), Severity.MEDIUM, 8),
]

# Negation guard: if a clearly-negative phrase wraps the keyword, it's benign.
_NEGATION_RE = re.compile(
    r"\b(no|not|without|never|isn'?t|aren'?t|non-|free of|doesn'?t|won'?t)\b"
    r".{0,40}?"
    r"(steal|credential|malware|exploit|virus|spy|phish|keylog|ransom|overlay|intercept)",
    re.I,
)

_PRIVILEGED_PERMISSIONS = {
    "android.permission.READ_SMS": (Severity.MEDIUM, 8),
    "android.permission.RECEIVE_SMS": (Severity.MEDIUM, 8),
    "android.permission.SEND_SMS": (Severity.MEDIUM, 8),
    "android.permission.READ_CONTACTS": (Severity.LOW, 3),
    "android.permission.READ_CALL_LOG": (Severity.MEDIUM, 8),
    "android.permission.READ_PHONE_STATE": (Severity.LOW, 3),
    "android.permission.READ_PHONE_NUMBERS": (Severity.LOW, 3),
    "android.permission.SYSTEM_ALERT_WINDOW": (Severity.HIGH, 12),
    "android.permission.BIND_ACCESSIBILITY_SERVICE": (Severity.HIGH, 15),
    "android.permission.REQUEST_INSTALL_PACKAGES": (Severity.MEDIUM, 8),
    "android.permission.WRITE_SETTINGS": (Severity.MEDIUM, 8),
    "android.permission.PACKAGE_USAGE_STATS": (Severity.MEDIUM, 8),
    "android.permission.CAMERA": (Severity.LOW, 2),
    "android.permission.RECORD_AUDIO": (Severity.LOW, 3),
    "android.permission.READ_EXTERNAL_STORAGE": (Severity.LOW, 2),
    "android.permission.WRITE_EXTERNAL_STORAGE": (Severity.LOW, 2),
    "android.permission.INTERNET": (Severity.INFO, 0),
    "android.permission.ACCESS_NETWORK_STATE": (Severity.INFO, 0),
    "android.permission.WAKE_LOCK": (Severity.LOW, 2),
    "android.permission.RECEIVE_BOOT_COMPLETED": (Severity.LOW, 3),
    "android.permission.FOREGROUND_SERVICE": (Severity.LOW, 3),
    "android.permission.BIND_DEVICE_ADMIN": (Severity.HIGH, 14),
    "android.permission.GET_ACCOUNTS": (Severity.LOW, 3),
    "android.permission.USE_CREDENTIALS": (Severity.LOW, 4),
}


def _is_negated(text: str, match_start: int) -> bool:
    """True if the 60 chars before the match contain a negation of a bad word."""
    window = text[max(0, match_start - 60): match_start]
    return bool(_NEGATION_RE.search(window + " " + text[match_start:match_start + 20]))


def scan_network(text: str, source: str) -> List[Signal]:
    out: List[Signal] = []
    seen = set()
    for rx in (_URL_RE, _DOMAIN_RE):
        for m in rx.finditer(text):
            val = m.group(0)
            if val.lower() in seen:
                continue
            seen.add(val.lower())
            out.append(Signal(
                signal_type=SignalType.NETWORK_INDICATOR,
                severity=Severity.MEDIUM,
                label="Network indicator",
                detail=val,
                evidence=val[:120],
                source_file=source,
                score=6,
            ))
    for m in _IPV4_RE.finditer(text):
        val = m.group(0)
        octets = [int(o) for o in val.split(".")]
        if any(o > 255 for o in octets):
            continue
        if val in seen:
            continue
        seen.add(val)
        # Skip obvious benign private/loopback in score-weighting but still record
        out.append(Signal(
            signal_type=SignalType.NETWORK_INDICATOR,
            severity=Severity.MEDIUM,
            label="IPv4 indicator",
            detail=val,
            evidence=val,
            source_file=source,
            score=5,
        ))
    return out


def scan_secrets(text: str, source: str) -> List[Signal]:
    out: List[Signal] = []
    for name, rx, sev, score in _SECRET_PATTERNS:
        for m in rx.finditer(text):
            val = m.group(0)
            # Avoid double-flagging within a negation context for generic keys
            if name.startswith("Generic") and _is_negated(text, m.start()):
                continue
            out.append(Signal(
                signal_type=SignalType.HARDCODED_SECRET,
                severity=sev,
                label=name,
                detail=val[:60] + ("…" if len(val) > 60 else ""),
                evidence=val[:120],
                source_file=source,
                score=score,
            ))
    return out


def scan_capabilities(text: str, source: str) -> List[Signal]:
    out: List[Signal] = []
    for name, rx, sev, score in _CAPABILITY_KEYWORDS:
        for m in rx.finditer(text):
            if _is_negated(text, m.start()):
                continue
            out.append(Signal(
                signal_type=SignalType.SUSPICIOUS_CAPABILITY,
                severity=sev,
                label=name,
                detail=m.group(0),
                evidence=m.group(0)[:120],
                source_file=source,
                score=score,
            ))
            break  # one signal per capability per file
    return out


def score_permission(perm: str):
    """Return (Severity, score) for a permission string, or None if uninteresting."""
    key = perm.strip()
    if key in _PRIVILEGED_PERMISSIONS:
        return _PRIVILEGED_PERMISSIONS[key]
    # Unknown custom permission: low informational
    if perm.startswith("com.") or "." in perm:
        return (Severity.LOW, 1)
    return None
