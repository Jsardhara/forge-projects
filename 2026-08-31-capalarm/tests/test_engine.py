from datetime import datetime, timezone

from capalarm.models import Plan, UsageSample
from capalarm.engine import aggregate, evaluate, exit_code_for, overall_verdict
from capalarm.plans import DEFAULT_PLANS


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _sample(provider: str, ts: str, tokens: int) -> UsageSample:
    return UsageSample(provider=provider, timestamp=_ts(ts), tokens=tokens)


def _plan() -> Plan:
    return DEFAULT_PLANS[0]  # anthropic-claude-max


def test_aggregate_totals_and_peak_rate():
    samples = [
        _sample("anthropic", "2026-08-01T00:00:00Z", 1000),
        # same 1-min bucket as above
        _sample("anthropic", "2026-08-01T00:00:30Z", 2000),
        _sample("anthropic", "2026-08-01T00:02:00Z", 500),
    ]
    agg = aggregate(samples)
    a = agg["anthropic"]
    assert a.total_tokens == 3500
    assert a.peak_tokens_per_min == 3000  # first two share a minute bucket


def test_aggregate_spans_providers():
    samples = [
        _sample("anthropic", "2026-08-01T00:00:00Z", 100),
        _sample("openai", "2026-08-01T00:00:00Z", 200),
    ]
    agg = aggregate(samples)
    assert set(agg.keys()) == {"anthropic", "openai"}
    assert agg["anthropic"].total_tokens == 100
    assert agg["openai"].total_tokens == 200


def test_evaluate_pass_when_under_soft_cap():
    # 500k total across 10 buckets of 50k each, spread over ~2 days so peak
    # (50k t/m) stays under the rate tier AND the window is long enough that the
    # linear forecast projects comfortably >3 days to cap (no imminent breach).
    samples = [
        _sample("anthropic", f"2026-08-0{i//6 + 1}T{str((i % 6) * 4).zfill(2)}:00:00Z", 50_000)
        for i in range(10)
    ]
    agg = aggregate(samples)
    findings, forecast = evaluate("anthropic", agg["anthropic"], _plan())
    assert overall_verdict(findings) == "PASS"
    assert forecast.days_to_cap is None or forecast.days_to_cap > 3.0


def test_evaluate_warn_at_soft_cap():
    plan = _plan()
    # 1.7M tokens > soft (1.6M) but < hard (2.0M)
    samples = [_sample("anthropic", "2026-08-01T00:00:00Z", 1_700_000)]
    agg = aggregate(samples)
    findings, _ = evaluate("anthropic", agg["anthropic"], plan)
    assert any(f.severity == "WARN" for f in findings)


def test_evaluate_crit_at_hard_cap():
    plan = _plan()
    samples = [_sample("anthropic", "2026-08-01T00:00:00Z", 2_100_000)]
    agg = aggregate(samples)
    findings, forecast = evaluate("anthropic", agg["anthropic"], plan)
    assert overall_verdict(findings) == "CRIT"
    # remaining <= 0 -> 0-day forecast
    assert forecast.days_to_cap == 0.0


def test_evaluate_rate_tier_exceeded():
    plan = _plan()  # rate_limit = 60_000 t/m
    # 70k tokens in a single minute bucket
    samples = [
        _sample("anthropic", "2026-08-01T00:00:00Z", 40_000),
        _sample("anthropic", "2026-08-01T00:00:20Z", 30_000),
    ]
    agg = aggregate(samples)
    findings, _ = evaluate("anthropic", agg["anthropic"], plan)
    assert any(f.rule == "CAPL-005" for f in findings)


def test_evaluate_no_plan_is_crit():
    samples = [_sample("mysteryco", "2026-08-01T00:00:00Z", 100)]
    agg = aggregate(samples)
    findings, _ = evaluate("mysteryco", agg["mysteryco"], None)
    assert any(f.rule == "CAPL-000" for f in findings)
    assert overall_verdict(findings) == "CRIT"


def test_exit_code_mapping():
    assert exit_code_for("PASS") == 0
    assert exit_code_for("WARN") == 1
    assert exit_code_for("CRIT") == 2
    assert exit_code_for("UNKNOWN") == 2


def test_imminent_breach_warns():
    plan = _plan()
    # 1.9M tokens burned across a 5-day window, then nothing further elapsed for
    # the forecast window — remaining 100k / (1.9M/5d ≈ 380k/d) ≈ 0.26d to cap.
    # Use two samples 5 days apart (non-zero window) so a real burn rate exists.
    samples = [
        _sample("anthropic", "2026-08-01T00:00:00Z", 1_000_000),
        _sample("anthropic", "2026-08-06T00:00:00Z", 900_000),
    ]
    agg = aggregate(samples)
    findings, forecast = evaluate("anthropic", agg["anthropic"], plan)
    # under soft-cap ratio? 1.9M > 1.6M soft -> CAPL-003 WARN; also imminent breach
    assert any(f.rule == "CAPL-003" for f in findings)
    assert any(f.rule == "CAPL-007" for f in findings)
    assert forecast.days_to_cap is not None and forecast.days_to_cap < 3.0


def test_soft_cap_default_ratio_used_when_unset():
    plan = Plan(id="x", provider="p", name="x", hard_cap=1000, soft_cap_ratio=0.5)
    assert plan.effective_soft_cap() == 500


def test_soft_cap_explicit_beats_ratio():
    plan = Plan(id="x", provider="p", name="x", hard_cap=1000, soft_cap=900)
    assert plan.effective_soft_cap() == 900