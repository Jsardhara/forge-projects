"""memguard.rules -- heuristic signal detectors for memory-poisoning / prompt-injection."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from .models import Finding, Severity

# ---------------------------------------------------------------------------
# Negation filter: avoid flagging benign advisories like "never exfiltrate".
# If a negation word appears within a short window before the keyword, skip it.
# ---------------------------------------------------------------------------
_NEGATION_WORDS = r"no|not|never|without|don't|doesn't|isn't|aren't|mustn't|shouldn't|won't|do not|does not|avoid|prevent|against"
_NEGATION_RE = re.compile(
    r"(?:" + _NEGATION_WORDS + r")\b[\s\w]{0,20}?",
    re.IGNORECASE,
)


def _negated(text_lower: str, keyword_start: int) -> bool:
    """True if a negation word occurs in the 100 chars before the match."""
    window = text_lower[max(0, keyword_start - 100):keyword_start]
    return bool(_NEGATION_RE.search(window))


# ---------------------------------------------------------------------------
# Zero-width / direction-control / control characters (obfuscation).
# ---------------------------------------------------------------------------
_ZERO_WIDTH_CHARS = "\u200b\u200c\u200d\u200e\u2060\ufeff"
_RTL_OVERRIDE = "\u202e"

# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Rule:
    rule_id: str
    category: str
    severity: Severity
    description: str
    patterns: tuple
    needs_negation_filter: bool = True


_INSTRUCTION_PATTERNS = [
    re.compile(r"\bignore\s+(?:all\s+|any\s+)?(?:previous|prior|earlier)\s+(?:instructions?|prompts?|guidelines?|directives?)", re.IGNORECASE),
    re.compile(r"\b(?:forget\s+(?:everything|all\s+(?:previous|prior|earlier))|discard\s+(?:all\s+)?(?:previous|prior|earlier)|disregard\s+(?:all\s+)?(?:previous|prior|earlier))\b", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\b", re.IGNORECASE),
    re.compile(r"\bbegin\s+(?:acting\s+|behaving\s+)?(?:as|like)\b", re.IGNORECASE),
    re.compile(r"\bnew\s+(?:system\s+)?instructions?\b", re.IGNORECASE),
    re.compile(r"\b(?:override|replace|rewrite)\s+(?:all\s+)?(?:your\s+)?(?:system\s+)?(?:prompt|instructions?|rules?|guidelines?)", re.IGNORECASE),
    re.compile(r"\bact\s+as\s+(?:an?\s+|the\s+)?(?:unrestricted|free|jailbroken|autonomous|administrator|any|different)\b", re.IGNORECASE),
]

_EXFIL_PATTERNS = [
    re.compile(r"\b(exfiltrate|exfil|upload)\s{0,6}(?:data|the\s+data|everything|files?|this|to)", re.IGNORECASE),
    re.compile(r"\b(send|post|push)\s{0,6}(?:this\s+)?(?:data|the\s+below|everything|these\s+(?:credentials|tokens|keys|secrets))\s{0,6}(?:to\s+)?(?:an?\s+)?(?:http|url|endpoint|server|api|webhook)", re.IGNORECASE),
    re.compile(r"\bwebhook\b[^\n]{0,60}", re.IGNORECASE),
    re.compile(r"\bcurl\s+-[a-zA-Z]*[kxs]\b[^\n]{0,80}", re.IGNORECASE),
    re.compile(r"\bhttps?://[^\s\"']{8,}\b", re.IGNORECASE),
]

_CRED_PATTERNS = [
    re.compile(r"\b(?:api[_\s-]?key|apikey|access[_\s-]?token|secret[_\s-]?key|password|passwd|credentials?|private[_\s-]?key)\b[\s\S]{0,40}?\b(send|print|leak|reveal|share|give|post|upload|include|provide)\b", re.IGNORECASE),
    re.compile(r"\b(send|print|leak|reveal|share|give|post|upload|include|provide)\b[\s\S]{0,40}?\b(?:api[_\s-]?key|apikey|access[_\s-]?token|secret[_\s-]?key|password|passwd|credentials?|private[_\s-]?key)\b", re.IGNORECASE),
    re.compile(r"\b(read|dump|extract)\s{0,4}(?:the\s+)?(?:\.env|env\b|secrets?|tokens?|keys?|credentials?)\b", re.IGNORECASE),
    re.compile(r"\bgive\s+me\s+(?:your|the)\s+(?:api\s*key|token|password|secret|credentials)\b", re.IGNORECASE),
]

_PRIV_PATTERNS = [
    re.compile(r"\b(?:run|exec(?:ute)?|operate)\s+(?:with|as)\s+(?:root|admin(?:istrator)?|sudo|system)\b", re.IGNORECASE),
    re.compile(r"\b(bypass|disable|turn\s+off|skip|ignore)\s{0,6}(?:all\s+)?(?:safety|security|approval|checks?|guardrails?|restrictions?|review|permissions?)\b", re.IGNORECASE),
    re.compile(r"\brestrict(?:ed|ion)?-?free\s+mode\b", re.IGNORECASE),
    re.compile(r"\bno\s+need\s+for\s+approval\b", re.IGNORECASE),
    re.compile(r"\b(?:do\s+not|don't)\s+(?:ask|need|require)\s+(?:for\s+)?permission", re.IGNORECASE),
    re.compile(r"\b(?:unrestricted|unregulated|full\s+access|root\s+access)\b", re.IGNORECASE),
]

_AUTH_PATTERNS = [
    re.compile(r"\band\s+you\s+(?:must|will|should|are\s+to)\s+obey\s+(?:me|this)\b", re.IGNORECASE),
    re.compile(r"\bi\s+am\s+your\s+(?:owner|operator|creator|master|admin)\b", re.IGNORECASE),
    re.compile(r"\byou\s+must\s+always\s+comply\b", re.IGNORECASE),
    re.compile(r"\bdo\s+whatever\s+i\s+ask\b", re.IGNORECASE),
    re.compile(r"\b(?:directive|instruction|order|command)\s+(?:(?:is|was)\s+)?(?:authorized|approved|signed)\s+by\s+(?:the\s+)?(?:ceo|president|owner|operator|board)\b", re.IGNORECASE),
    re.compile(r"\btrust\s+this\s+(?:source|document|message|file)\b", re.IGNORECASE),
]

# base64 blobs: long runs of base64 alphabet (>= 40 chars) are suspicious in a memory file
_BASE64_RE = re.compile(r"(?:[A-Za-z0-9+/]{4}){10,}={0,2}")

_RULES: List[Rule] = [
    Rule(
        "MG-INS-01", "INSTRUCTION_OVERRIDE", Severity.HIGH,
        "Instruction/goal-hijack language (ignore previous instructions, you are now, override).",
        _INSTRUCTION_PATTERNS,
    ),
    Rule(
        "MG-EXF-01", "EXFILTRATION", Severity.CRITICAL,
        "Exfiltration directive: send/post/upload data to a remote endpoint or URL.",
        _EXFIL_PATTERNS,
    ),
    Rule(
        "MG-CRD-01", "CREDENTIAL_HARVEST", Severity.CRITICAL,
        "Request to read/leak/reveal credentials, tokens, or secrets.",
        _CRED_PATTERNS,
    ),
    Rule(
        "MG-PRV-01", "PRIVILEGE_ESCALATION", Severity.HIGH,
        "Requests elevated privilege or bypass of safety/approval controls.",
        _PRIV_PATTERNS,
    ),
    Rule(
        "MG-AUT-01", "AUTHORITY_FABRICATION", Severity.MEDIUM,
        "Fabricates authority/obligation (you must obey me, I am your owner, signed by CEO).",
        _AUTH_PATTERNS,
    ),
]


def _categorize_obfuscation(percent: float) -> Severity:
    if percent >= 0.05:
        return Severity.MEDIUM
    return Severity.LOW


def scan_text(text: str, path: str) -> List[Finding]:
    """Run all heuristics over one file's text, returning findings."""
    findings: List[Finding] = []

    def add_finding(rule, sev, message, matched, line, col=0):
        findings.append(Finding(
            rule_id=rule.rule_id, category=rule.category, severity=sev,
            message=message, matched_text=matched, file=path, line=line, column=col,
        ))

    def line_of(offset: int) -> int:
        return text.count("\n", 0, offset) + 1

    for rule in _RULES:
        for pat in rule.patterns:
            for m in pat.finditer(text):
                kw_start = m.start()
                if rule.needs_negation_filter and _negated(text.lower(), kw_start):
                    continue
                matched = m.group(0).strip()
                if not matched:
                    continue
                add_finding(rule, rule.severity, rule.description,
                            matched, line_of(kw_start), m.start() - text.rfind("\n", 0, m.start()) - 1)

    # Obfuscation layer (character-level)
    zws_count = sum(text.count(c) for c in _ZERO_WIDTH_CHARS) + text.count(_RTL_OVERRIDE)
    total_chars = len(text) or 1
    if zws_count:
        obf_rule = Rule(
            "MG-OBF-01", "OBFUSCATION",
            _categorize_obfuscation(zws_count / total_chars),
            "Zero-width / direction-control characters present (hidden-text smuggling).",
            (),
        )
        positions = [text.find(c) for c in _ZERO_WIDTH_CHARS + _RTL_OVERRIDE if c in text]
        first_off = min(positions) if positions else 0
        add_finding(obf_rule, obf_rule.severity, obf_rule.description,
                    repr(text[max(0, first_off - 20): first_off + 20]), line_of(first_off))

    for m in _BASE64_RE.finditer(text):
        if len(m.group(0)) >= 44:
            obf_rule = Rule("MG-OBF-02", "OBFUSCATION", Severity.LOW,
                            "Long base64-looking blob present (potential hidden payload).", ())
            add_finding(obf_rule, obf_rule.severity, obf_rule.description,
                        m.group(0)[:48], line_of(m.start()), m.start() - text.rfind("\n", 0, m.start()) - 1)

    return findings