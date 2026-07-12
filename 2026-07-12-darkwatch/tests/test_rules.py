"""Tests for individual dark-pattern rules. TDD: each rule fires on its fixture
and stays silent on the clean fixture (or its negation-clean variant)."""
from __future__ import annotations

from darkwatch.rules import (  # noqa: E402
    ConfusingLanguageRule,
    DisguisedAdRule,
    FakeUrgencyRule,
    ForcedContinuityRule,
    MismatchedConsentRule,
    MinorAddictiveRule,
    PrecheckedOptInRule,
    RoachMotelCancelRule,
)
from darkwatch.rules import parse_html  # noqa: E402
from fixtures import (  # noqa: E402
    CLEAN_HTML,
    CONFUSING_HTML,
    DISGUISED_AD_HTML,
    FAKE_URGENCY_HTML,
    FORCED_CONTINUITY_CLEAN_HTML,
    FORCED_CONTINUITY_HTML,
    MISMATCHED_HTML,
    MINOR_ADDICTIVE_CLEAN_HTML,
    MINOR_ADDICTIVE_HTML,
    PRECHECKED_HTML,
    ROACH_MOTEL_HTML,
)


def _find(rule, html):
    return rule.scan(parse_html(html), "test")


def test_roach_motel_fires():
    f = _find(RoachMotelCancelRule(), ROACH_MOTEL_HTML)
    assert f is not None and f.rule_id == "roach_motel_cancel"
    assert "call" in f.evidence.lower() or "cancel" in f.evidence.lower()


def test_roach_motel_clean():
    assert _find(RoachMotelCancelRule(), CLEAN_HTML) is None


def test_prechecked_fires():
    f = _find(PrecheckedOptInRule(), PRECHECKED_HTML)
    assert f is not None and f.rule_id == "prechecked_optin"


def test_prechecked_clean():
    assert _find(PrecheckedOptInRule(), CLEAN_HTML) is None


def test_forced_continuity_fires():
    f = _find(ForcedContinuityRule(), FORCED_CONTINUITY_HTML)
    assert f is not None and f.rule_id == "forced_continuity"


def test_forced_continuity_negation_clean():
    assert _find(ForcedContinuityRule(), FORCED_CONTINUITY_CLEAN_HTML) is None


def test_confusing_fires():
    f = _find(ConfusingLanguageRule(), CONFUSING_HTML)
    assert f is not None and f.rule_id == "confusing_language"
    assert "unsubscribe" in f.evidence.lower()


def test_confusing_clean():
    assert _find(ConfusingLanguageRule(), CLEAN_HTML) is None


def test_fake_urgency_fires():
    f = _find(FakeUrgencyRule(), FAKE_URGENCY_HTML)
    assert f is not None and f.rule_id == "fake_urgency"


def test_fake_urgency_clean():
    assert _find(FakeUrgencyRule(), CLEAN_HTML) is None


def test_mismatched_fires():
    f = _find(MismatchedConsentRule(), MISMATCHED_HTML)
    assert f is not None and f.rule_id == "mismatched_consent"


def test_mismatched_clean():
    assert _find(MismatchedConsentRule(), CLEAN_HTML) is None


def test_disguised_ad_fires():
    f = _find(DisguisedAdRule(), DISGUISED_AD_HTML)
    assert f is not None and f.rule_id == "disguised_ad"


def test_disguised_ad_clean():
    assert _find(DisguisedAdRule(), CLEAN_HTML) is None


def test_minor_addictive_fires():
    f = _find(MinorAddictiveRule(), MINOR_ADDICTIVE_HTML)
    assert f is not None and f.rule_id == "minor_addictive"


def test_minor_addictive_age_gate_clean():
    assert _find(MinorAddictiveRule(), MINOR_ADDICTIVE_CLEAN_HTML) is None
