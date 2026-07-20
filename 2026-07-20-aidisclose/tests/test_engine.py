"""Engine tests: applicability, gap scoring, risk bands, watch-path.

Uses a hand-built small mandate set for deterministic scores, plus one
integration test against the real curated dataset.
"""
from datetime import date

from aidisclose.engine import analyze, mandate_applies
from aidisclose.models import (
    Mandate, MandateStatus, Obligation, OrgProfile, Severity,
)
from aidisclose.rules import load_mandates

from fixtures import make_profile

REF = date(2026, 7, 20)


def _m_hire():
    return Mandate(
        mid="t-hire", jurisdiction="US-NY", title="T Hire", summary="x",
        status=MandateStatus.IN_FORCE, effective_date=date(2020, 1, 1),
        scope_sectors=("employment",), scope_uses=("hiring",),
        obligations=(
            Obligation("audit", "Audit", "x", Severity.CRITICAL),   # 10
            Obligation("disc", "Disclose", "x", Severity.HIGH),     # 6
        ),
    )


def _m_bio():
    return Mandate(
        mid="t-bio", jurisdiction="US-IL", title="T Bio", summary="x",
        status=MandateStatus.IN_FORCE, effective_date=date(2020, 1, 1),
        scope_sectors=None, scope_uses=("biometric",),
        obligations=(
            Obligation("consent", "Consent", "x", Severity.CRITICAL),  # 10
            Obligation("retain", "Retain", "x", Severity.LOW),         # 1
        ),
    )


def _m_prop():
    # matches same scope as hire but PROPOSED -> monitored, never scored
    return Mandate(
        mid="t-prop", jurisdiction="US-NY", title="T Prop", summary="x",
        status=MandateStatus.PROPOSED, effective_date=None,
        scope_sectors=("employment",), scope_uses=("hiring",),
        obligations=(Obligation("xyz", "Xyz", "x", Severity.HIGH),),
    )


def _m_future():
    # IN_FORCE but effective in the far future -> watched, not scored
    return Mandate(
        mid="t-future", jurisdiction="US-NY", title="T Future", summary="x",
        status=MandateStatus.IN_FORCE, effective_date=date(2099, 1, 1),
        scope_sectors=("employment",), scope_uses=("hiring",),
        obligations=(Obligation("f", "F", "x", Severity.HIGH),),
    )


def _mini():
    return (_m_hire(), _m_bio(), _m_prop(), _m_future())


def test_full_gap_blocks():
    p = make_profile(jurisdictions=["US-NY"], sectors=["employment"],
                     ai_uses=["hiring"])
    r = analyze(p, _mini())
    assert r.applicable_count == 1          # only t-hire (t-prop + t-future monitored)
    assert r.monitored_count == 2           # t-prop (proposed) + t-future (not yet effective)
    assert r.score == 100.0
    assert r.band == "CRITICAL"
    assert r.blocking is True               # audit is critical + unmet


def test_no_gap_low():
    p = make_profile(jurisdictions=["US-NY"], sectors=["employment"],
                     ai_uses=["hiring"], implemented=["audit", "disc"])
    r = analyze(p, _mini())
    assert r.score == 0.0
    assert r.band == "LOW"
    assert r.blocking is False


def test_partial_gap_high_band():
    # hire unmet disc (6); bio unmet consent(10)+retain(1)=11
    p = make_profile(jurisdictions=["US-NY", "US-IL"], sectors=["employment"],
                     ai_uses=["hiring", "biometric"], implemented=["audit"])
    r = analyze(p, _mini())
    assert r.applicable_count == 2
    total_gap = 6 + 11
    total_possible = 16 + 11
    # r.score is rounded to 2 decimals
    assert abs(r.score - round(100.0 * total_gap / total_possible, 2)) < 1e-9
    assert r.band == "HIGH"                 # 62.96 >= 50
    assert r.blocking is True


def test_sector_filter_no_match():
    p = make_profile(jurisdictions=["US-NY"], sectors=["real_estate"],
                     ai_uses=["hiring"])
    r = analyze(p, _mini())
    assert r.applicable_count == 0
    assert r.monitored_count == 0
    assert r.score == 0.0
    assert r.blocking is False              # no div-by-zero, safe default


def test_future_mandate_watched_not_scored():
    p = make_profile(jurisdictions=["US-NY"], sectors=["employment"],
                     ai_uses=["hiring"])
    # remove t-prop so the only match is t-hire (scored) + t-future (watched)
    mini = (_m_hire(), _m_bio(), _m_future())
    r = analyze(p, mini)
    assert r.applicable_count == 1
    assert r.monitored_count == 1           # t-future
    assert r.score == 100.0                 # t-hire fully unmet, t-future ignored


def test_mandate_applies_helper():
    p = make_profile(jurisdictions=["US-NY"], sectors=["employment"],
                     ai_uses=["hiring"])
    assert mandate_applies(p, _m_hire()) is True
    assert mandate_applies(p, _m_bio()) is False   # wrong jurisdiction/use
    assert mandate_applies(p, _m_prop()) is True   # scope matches (status irrelevant here)


def test_real_dataset_analysis_runs():
    p = make_profile(name="RealCo", jurisdictions=["US-NY", "EU"],
                     sectors=["employment", "real_estate"],
                     ai_uses=["hiring", "content_generation", "listing_generation"])
    r = analyze(p)                          # uses curated dataset
    assert r.reference_date == REF
    assert r.applicable_count >= 1
    # every applicable mandate must be IN_FORCE with an arrived effective date
    for am in r.applicable:
        assert am.mandate.status == MandateStatus.IN_FORCE
    # monitored must include at least the proposed NYC listing entry for this profile
    monitored_ids = {m.mid for m in r.monitored}
    assert "nyc-listing-ai" in monitored_ids
