from __future__ import annotations

from datetime import datetime, timedelta, timezone

from exfilsentinel.detector import (
    ALLOWLIST_CREDIT,
    OFFBOARDING_BOOST,
    DetectionEngine,
    _clamp,
)
from exfilsentinel.models import ApiEvent, RiskClass

UTC = timezone.utc


def _e(actor, model, ts_min=0, ct=0, pt=0, endpoint="/v1/chat/completions",
       ip="", tmpl=""):
    return ApiEvent(
        actor_id=actor,
        model=model,
        timestamp=datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC) + timedelta(minutes=ts_min),
        prompt_tokens=pt,
        completion_tokens=ct,
        endpoint=endpoint,
        ip=ip,
        prompt_template_hash=tmpl,
    )


def test_clamp_bounds():
    assert _clamp(-1.0) == 0.0
    assert _clamp(2.0) == 1.0
    assert _clamp(0.4) == 0.4


def test_no_events_is_benign():
    v = DetectionEngine().evaluate("a1", [])
    assert v.risk_score == 0.0
    assert v.risk_class == RiskClass.BENIGN
    assert v.triggered == ()


def test_competing_actor_excluded():
    # Same event list, but we evaluate a different actor -> no events -> benign.
    events = [_e("other", "gpt-4", ct=2_000_000)]
    v = DetectionEngine().evaluate("a1", events)
    assert v.risk_class == RiskClass.BENIGN


def test_single_signal_equals_its_raw_score():
    # One triggered signal -> normalized risk == that signal's raw score.
    events = [_e("a1", "ft:secret-model", ct=10, pt=10)]
    v = DetectionEngine().evaluate("a1", events)
    sig = next(s for s in v.signals if s.name == "sensitive_model_access")
    assert sig.raw_score == 0.5
    assert v.risk_score == 0.5
    assert v.risk_class == RiskClass.SUSPICIOUS


def test_volume_burst_scales_linearly():
    eng = DetectionEngine()
    # single events, prompt==completion so completion_heavy stays 0 (only volume_burst triggers)
    half = [_e("a1", "gpt-4", ct=500_000, pt=500_000)]
    full = [_e("a1", "gpt-4", ct=1_000_000, pt=1_000_000)]
    sh = eng.evaluate("a1", half)
    sf = eng.evaluate("a1", full)
    assert abs(sh.risk_score - 0.5) < 1e-9
    assert abs(sf.risk_score - 1.0) < 1e-9


def test_repetitive_prompt_detects_low_diversity():
    # 50 identical prompts -> diversity ~0 -> raw ~1.0
    base = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)
    events = [
        ApiEvent("a1", "gpt-4", base + timedelta(minutes=i), 100, 100,
                 prompt_template_hash="same-tmpl")
        for i in range(50)
    ]
    v = DetectionEngine().evaluate("a1", events)
    rep = next(s for s in v.signals if s.name == "repetitive_prompt")
    assert rep.raw_score > 0.9


def test_repetitive_prompt_low_for_diverse():
    base = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)
    events = [
        ApiEvent("a1", "gpt-4", base + timedelta(minutes=i), 100, 100,
                 prompt_template_hash=f"tmpl-{i}")
        for i in range(50)
    ]
    v = DetectionEngine().evaluate("a1", events)
    rep = next(s for s in v.signals if s.name == "repetitive_prompt")
    assert rep.raw_score < 0.1


def test_rate_spike_detection():
    base = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)
    # 100 requests within ~10 seconds -> high rps
    events = [
        ApiEvent("a1", "gpt-4", base + timedelta(milliseconds=100 * i), 10, 10)
        for i in range(100)
    ]
    v = DetectionEngine().evaluate("a1", events)
    rs = next(s for s in v.signals if s.name == "rate_spike")
    assert rs.raw_score > 0.9


def test_rate_spike_human_pace_is_clean():
    base = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)
    # 5 requests spread over 600 seconds -> 0.008 rps, below human pace
    events = [
        ApiEvent("a1", "gpt-4", base + timedelta(seconds=i * 120), 10, 10)
        for i in range(5)
    ]
    v = DetectionEngine().evaluate("a1", events)
    rs = next(s for s in v.signals if s.name == "rate_spike")
    assert rs.raw_score == 0.0


def test_completion_heavy_ratio():
    # pure completion harvesting: prompt 1, completion 999 -> ratio 0.999 -> raw~1.0
    events = [_e("a1", "gpt-4", pt=1, ct=999)]
    v = DetectionEngine().evaluate("a1", events)
    ch = next(s for s in v.signals if s.name == "completion_heavy")
    assert ch.raw_score > 0.9
    # balanced: prompt 500, completion 500 -> ratio 0.5 -> raw 0.0
    events2 = [_e("a1", "gpt-4", pt=500, ct=500)]
    v2 = DetectionEngine().evaluate("a1", events2)
    ch2 = next(s for s in v2.signals if s.name == "completion_heavy")
    assert ch2.raw_score == 0.0


def test_download_pattern_endpoint():
    events = [_e("a1", "gpt-4", ct=10, endpoint="/v1/models/ft-x/download")]
    v = DetectionEngine().evaluate("a1", events)
    dp = next(s for s in v.signals if s.name == "download_pattern")
    assert dp.raw_score == 0.5


def test_off_hours_night():
    # all events between 00:00 and 06:00
    events = [
        ApiEvent("a1", "gpt-4", datetime(2026, 7, 11, h, 0, 0, tzinfo=UTC), 10, 10)
        for h in range(6)
    ]
    v = DetectionEngine().evaluate("a1", events)
    oh = next(s for s in v.signals if s.name == "off_hours")
    assert oh.raw_score == 1.0


def test_offboarding_boost():
    base = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)
    ob_since = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)
    events = [
        ApiEvent("a1", "ft:secret", base + timedelta(days=-10), 10, 1_000_000)
    ]
    v_no = DetectionEngine().evaluate("a1", events)
    v_yes = DetectionEngine().evaluate("a1", events, offboarding_since=ob_since)
    assert v_no.risk_score < v_yes.risk_score
    assert v_yes.risk_score == _clamp(v_no.risk_score * OFFBOARDING_BOOST)
    ob = next(s for s in v_yes.signals if s.name == "offboarding_window")
    assert ob.raw_score == 1.0


def test_offboarding_window_outside_grace_is_zero():
    base = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)
    ob_since = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)
    # event 60 days before offboarding (outside 30-day grace)
    events = [
        ApiEvent("a1", "ft:secret", base + timedelta(days=-60), 10, 1_000_000)
    ]
    v = DetectionEngine().evaluate("a1", events, offboarding_since=ob_since)
    ob = next(s for s in v.signals if s.name == "offboarding_window")
    assert ob.raw_score == 0.0


def test_allowlist_credit_reduces_risk():
    events = [_e("a1", "ft:secret", ct=1_000_000)]
    v_no = DetectionEngine().evaluate("a1", events)
    v_yes = DetectionEngine().evaluate("a1", events, allowlisted=True)
    assert abs(v_yes.risk_score - _clamp(v_no.risk_score - ALLOWLIST_CREDIT)) < 1e-3
    assert "allowlisted" in v_yes.evidence[-1]


def test_classification_boundaries():
    eng = DetectionEngine()
    # Single download-pattern hit with ct=0 (completion_heavy raw=0): only
    # download_pattern (raw=0.5, w=0.30) triggers -> risk 0.5, SUSPICIOUS.
    v1 = eng.evaluate("a1", [_e("a1", "gpt-4", ct=0, pt=100, endpoint="/v1/files/export")])
    assert v1.risk_class == RiskClass.SUSPICIOUS
    assert abs(v1.risk_score - 0.5) < 1e-9
    v2 = eng.evaluate("a1", [_e("a1", "gpt-4", ct=0, pt=100, endpoint="/v1/files/export")])
    assert 0.25 < v2.risk_score <= 0.65
    assert v2.risk_class == RiskClass.SUSPICIOUS
    # Exfiltration: sensitive model + huge volume -> high risk
    ev = [_e("a1", "ft:secret-weights", ct=5_000_000)]
    v3 = eng.evaluate("a1", ev)
    assert v3.risk_class == RiskClass.EXFILTRATION


def test_evaluated_at_is_aware():
    v = DetectionEngine().evaluate("a1", [_e("a1", "ft:secret", ct=10)])
    assert v.evaluated_at.tzinfo is not None
