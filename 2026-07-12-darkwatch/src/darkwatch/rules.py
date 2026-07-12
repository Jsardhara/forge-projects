"""Dark-pattern detection rules.

Eight heuristic rules mapped to four regulations. Stateless, HTML-aware, and
negation-filtered where a benign phrasing would otherwise cause a false positive.

Rule design notes (TDD targets live in tests/test_rules.py):
  - Every rule must fire on a *crafted fixture* and stay silent on a *clean* fixture.
  - Forced-continuity uses a negation filter so "no automatic renewal" stays clean.
  - Minor-addictive is suppressed when an explicit age-gate ("18+") is present.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import List, Optional

from .models import Finding, Regulation, Severity

# Regexes compiled once.
_NEGATION_RE = re.compile(
    r"\b(no|not|without|never|won'?t|isn'?t|aren'?t|doesn'?t|don'?t)\b.{0,40}"
    r"(automatic renewal|auto.?renew|recurring|charge|subscription|subscribe)",
    re.IGNORECASE,
)
_CONFUSING_RE = re.compile(
    r"unsubscribe.{0,40}(charged|billed|bill|pay|payment)", re.IGNORECASE
)
_SCARCITY_RE = re.compile(
    r"\b(only|just)\s+\d+\s+(left|remaining|spots|seats|places)\b"
    r"|\boffer (ends|expires) (in|soon|tonight|today|at midnight)\b"
    r"|\bhurry\b.{0,20}(sell|gone|ends|expires)",
    re.IGNORECASE,
)
_TRIAL_RE = re.compile(
    r"free (trial|trial|demo period)|start your free", re.IGNORECASE
)
_RENEWAL_RE = re.compile(
    r"(auto[.\- ]?renew|renews|recurring (charge|payment|billing)|subscription (continues|will continue))",
    re.IGNORECASE,
)
_MINOR_ADDICT_RE = re.compile(
    r"(daily streak|streak (bonus|reward)|claim your (daily )?reward|daily reward|"
    r"spin to (win|earn)|loot box|lootbox|come back (every|daily)|check in (every|daily))",
    re.IGNORECASE,
)
_AGE_GATE_RE = re.compile(r"\b(18\+|18 and over|age gate|age verification|must be 18)\b", re.IGNORECASE)
_CANCEL_LINK_RE = re.compile(r"cancel", re.IGNORECASE)
_SIGNUP_RE = re.compile(
    r"(subscribe|sign[ -]?up|free trial|premium (plan|membership)|start (your )?membership|join (now|today|premium))",
    re.IGNORECASE,
)


@dataclass
class HtmlContext:
    """Parsed view of a page: full lowercased text + per-element (tag, attrs, text)."""

    text: str
    elements: List[dict]  # each: {"tag": str, "attrs": dict, "text": str}

    @property
    def raw_text(self) -> str:
        return self.text

    def has(self, pattern: re.Pattern) -> bool:
        return bool(pattern.search(self.text))

    def find_elements(self, tag: str, **attr_substr) -> List[dict]:
        out = []
        want = {k.lower(): v.lower() for k, v in attr_substr.items()}
        for el in self.elements:
            if el["tag"] != tag:
                continue
            ok = True
            for ak, av in want.items():
                val = " ".join(str(v) for v in el["attrs"].get(ak, []))
                if av not in val.lower():
                    ok = False
                    break
            if ok:
                out.append(el)
        return out


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: List[dict] = []
        self._body: List[str] = []
        self._stack: List[dict] = []

    def handle_starttag(self, tag, attrs):
        d = {"tag": tag.lower(), "attrs": {}, "text": ""}
        for k, v in attrs:
            d["attrs"].setdefault(k.lower(), []).append(v if v is not None else "")
        self.elements.append(d)
        self._stack.append(d)

    def handle_data(self, data):
        if data.strip():
            self._body.append(data)
            if self._stack:
                self._stack[-1]["text"] += data

    def handle_endtag(self, tag):
        if self._stack:
            self._stack.pop()


def parse_html(html: str) -> HtmlContext:
    p = _PageParser()
    p.feed(html)
    text = " ".join(p._body)
    return HtmlContext(text=text.lower(), elements=p.elements)


# --------------------------------------------------------------------------
# Rule base
# --------------------------------------------------------------------------
class Rule:
    id: str = "rule"
    title: str = "rule"
    regulation: Regulation = Regulation.NYC_SUBSCRIPTIONS
    severity: Severity = Severity.MEDIUM

    def scan(self, ctx: HtmlContext, url: str) -> Optional[Finding]:  # pragma: no cover
        raise NotImplementedError

    def _finding(self, ctx: HtmlContext, url: str, evidence: str) -> Finding:
        return Finding(
            rule_id=self.id,
            title=self.title,
            description=self._description(),
            regulation=self.regulation,
            severity=self.severity,
            evidence=evidence[:300],
            url=url,
        )

    def _description(self) -> str:
        return (
            f"Detected a potential {self.severity.value} dark-pattern under "
            f"{self.regulation.value}."
        )


# --------------------------------------------------------------------------
# Rule 1 — Roach-motel cancel flow (NYC Subscriptions)
# --------------------------------------------------------------------------
class RoachMotelCancelRule(Rule):
    id = "roach_motel_cancel"
    title = "Hard-to-cancel (roach-motel) flow"
    regulation = Regulation.NYC_SUBSCRIPTIONS
    severity = Severity.HIGH

    def scan(self, ctx: HtmlContext, url: str) -> Optional[Finding]:
        signup = ctx.has(_SIGNUP_RE)
        cancel_links = ctx.find_elements("a", href="cancel") + [
            e for e in ctx.elements
            if e["tag"] in ("a", "button") and _CANCEL_LINK_RE.search(e["text"])
        ]
        call_to_cancel = re.search(r"to cancel.{0,30}call", ctx.text)
        if not signup:
            return None
        if not cancel_links:
            return self._finding(
                ctx, url,
                "Subscription/signup flow present but no visible cancel link or button found.",
            )
        if call_to_cancel:
            return self._finding(
                ctx, url,
                "Cancel flow routes through a phone call: '{}'".format(call_to_cancel.group(0)),
            )
        return None


# --------------------------------------------------------------------------
# Rule 2 — Pre-checked opt-in (EU UCPD)
# --------------------------------------------------------------------------
class PrecheckedOptInRule(Rule):
    id = "prechecked_optin"
    title = "Pre-checked consent box"
    regulation = Regulation.EU_UCPD
    severity = Severity.HIGH

    _CONSENT_KW = re.compile(
        r"(subscribe|newsletter|marketing|updates|offers|promotions|receive (emails|news))",
        re.IGNORECASE,
    )

    def scan(self, ctx: HtmlContext, url: str) -> Optional[Finding]:
        checkboxes = ctx.find_elements("input", type="checkbox") + ctx.find_elements(
            "input", type="radio"
        )
        checked = [c for c in checkboxes if "checked" in c["attrs"]]
        if not checked:
            return None
        # Find a consent label near any checked box.
        labels = [e for e in ctx.elements if e["tag"] == "label"]
        for c in checked:
            ctext = c["text"]
            for lab in labels:
                # crude proximity: same substring window not tracked; match by text keywords
                if self._CONSENT_KW.search(lab["text"]) or self._CONSENT_KW.search(ctext):
                    return self._finding(
                        ctx, url,
                        "Default-checked box with consent language: '{}'".format(
                            (lab["text"] or ctext)[:160]
                        ),
                    )
        return None


# --------------------------------------------------------------------------
# Rule 3 — Forced continuity (FTC Negative-Option)
# --------------------------------------------------------------------------
class ForcedContinuityRule(Rule):
    id = "forced_continuity"
    title = "Forced continuity / unclear auto-renewal"
    regulation = Regulation.FTC_NEGATIVE_OPTION
    severity = Severity.MEDIUM

    def scan(self, ctx: HtmlContext, url: str) -> Optional[Finding]:
        if not (ctx.has(_TRIAL_RE) and ctx.has(_RENEWAL_RE)):
            return None
        if _NEGATION_RE.search(ctx.text):
            return None  # explicit "no automatic renewal" disclosure present
        return self._finding(
            ctx, url,
            "Free-trial offer paired with auto-renewal language without clear negation disclosure.",
        )


# --------------------------------------------------------------------------
# Rule 4 — Confusing language / mislabeled action (EU UCPD)
# --------------------------------------------------------------------------
class ConfusingLanguageRule(Rule):
    id = "confusing_language"
    title = "Confusing cancellation language"
    regulation = Regulation.EU_UCPD
    severity = Severity.MEDIUM

    def scan(self, ctx: HtmlContext, url: str) -> Optional[Finding]:
        m = _CONFUSING_RE.search(ctx.text)
        if not m:
            return None
        return self._finding(ctx, url, "'$s'".replace("$s", m.group(0)))


# --------------------------------------------------------------------------
# Rule 5 — Fake urgency / scarcity (EU DSA manipulative design)
# --------------------------------------------------------------------------
class FakeUrgencyRule(Rule):
    id = "fake_urgency"
    title = "Manipulative urgency / scarcity"
    regulation = Regulation.EU_DSA
    severity = Severity.MEDIUM

    def scan(self, ctx: HtmlContext, url: str) -> Optional[Finding]:
        countdown = ctx.find_elements("div", class_="countdown") + ctx.find_elements(
            "span", class_="timer"
        )
        timer_script = "countdown" in ctx.text or "setinterval" in ctx.text
        scarcity = _SCARCITY_RE.search(ctx.text)
        if countdown or timer_script or scarcity:
            ev = scarcity.group(0) if scarcity else (
                "countdown/timer element present" if countdown else "timer script detected"
            )
            return self._finding(ctx, url, ev)
        return None


# --------------------------------------------------------------------------
# Rule 6 — Mismatched consent (box does more than label says) (EU UCPD)
# --------------------------------------------------------------------------
class MismatchedConsentRule(Rule):
    id = "mismatched_consent"
    title = "Mismatched consent (label understates function)"
    regulation = Regulation.EU_UCPD
    severity = Severity.MEDIUM

    _MARKETING_ATTR = re.compile(r"(subscribe|newsletter|marketing|opt|promo)", re.IGNORECASE)
    _TERMS_ONLY = re.compile(r"(terms|conditions|privacy)", re.IGNORECASE)

    def scan(self, ctx: HtmlContext, url: str) -> Optional[Finding]:
        boxes = ctx.find_elements("input", type="checkbox") + ctx.find_elements(
            "input", type="radio"
        )
        labels = [e for e in ctx.elements if e["tag"] == "label"]
        for b in boxes:
            attr_blob = " ".join(
                str(v) for vals in b["attrs"].values() for v in vals
            )
            if not self._MARKETING_ATTR.search(attr_blob):
                continue
            label_text = ""
            for lab in labels:
                if self._TERMS_ONLY.search(lab["text"]) and not self._MARKETING_ATTR.search(
                    lab["text"]
                ):
                    label_text = lab["text"]
                    break
            if label_text:
                return self._finding(
                    ctx, url,
                    "Box with marketing attr labeled only as '{}'".format(label_text[:120]),
                )
        return None


# --------------------------------------------------------------------------
# Rule 7 — Disguised advertisement (EU UCPD / DSA transparency)
# --------------------------------------------------------------------------
class DisguisedAdRule(Rule):
    id = "disguised_ad"
    title = "Disguised advertisement"
    regulation = Regulation.EU_UCPD
    severity = Severity.LOW

    _AD_ATTR = re.compile(r"(sponsored|promoted|native[-_]?ad|in[-_]?feed[-_]?ad)", re.IGNORECASE)

    def scan(self, ctx: HtmlContext, url: str) -> Optional[Finding]:
        for el in ctx.elements:
            attr_blob = " ".join(str(v) for vals in el["attrs"].values() for v in vals)
            if self._AD_ATTR.search(attr_blob):
                if "advertisement" not in el["text"].lower():
                    return self._finding(
                        ctx, url,
                        "Ad-flagged element without 'advertisement' disclosure: class '{}'".format(
                            attr_blob[:120]
                        ),
                    )
        return None


# --------------------------------------------------------------------------
# Rule 8 — Minor-addictive design (EU DSA Art. 25)
# --------------------------------------------------------------------------
class MinorAddictiveRule(Rule):
    id = "minor_addictive"
    title = "Addictive-design engagement loops"
    regulation = Regulation.EU_DSA
    severity = Severity.MEDIUM

    def scan(self, ctx: HtmlContext, url: str) -> Optional[Finding]:
        if not ctx.has(_MINOR_ADDICT_RE):
            return None
        if _AGE_GATE_RE.search(ctx.text):
            return None  # explicit age-gate present -> not minor-facing
        m = _MINOR_ADDICT_RE.search(ctx.text)
        return self._finding(ctx, url, "'$s'".replace("$s", (m.group(0) if m else "engagement loop")))


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------
ALL_RULES: List[Rule] = [
    RoachMotelCancelRule(),
    PrecheckedOptInRule(),
    ForcedContinuityRule(),
    ConfusingLanguageRule(),
    FakeUrgencyRule(),
    MismatchedConsentRule(),
    DisguisedAdRule(),
    MinorAddictiveRule(),
]

RULES_BY_ID = {r.id: r for r in ALL_RULES}
