from tokenaudit.models import Usage, CostReport, WasteFinding, PhaseBreakdown


def test_usage_total():
    u = Usage(input_tokens=100, output_tokens=50)
    assert u.total == 150
    assert u.total_with_cache == 150


def test_usage_total_with_cache():
    u = Usage(input_tokens=100, output_tokens=50, cache_creation_tokens=10, cache_read_tokens=20)
    assert u.total_with_cache == 180


def test_cost_report_wasted_accessors():
    f1 = WasteFinding("PRE_READ_OVERHEAD", "HIGH", "x", wasted_tokens=1000, wasted_cost=0.03)
    f2 = WasteFinding("REDUNDANT_READS", "WARN", "y", wasted_tokens=500, wasted_cost=0.01)
    rep = CostReport(session="s", agent="generic", findings=[f1, f2])
    assert rep.wasted_tokens == 1500
    assert abs(rep.wasted_cost - 0.04) < 1e-9


def test_cost_report_as_dict_roundtrip():
    rep = CostReport(
        session="sess.jsonl",
        agent="claude-code",
        total_input=1000,
        total_output=200,
        total_cost=0.0123,
        by_model={"claude-sonnet-4": 0.0123},
        phase=PhaseBreakdown(preread_input=800, tool_result_input=200, other_input=0, generation_output=200),
        findings=[WasteFinding("PRE_READ_OVERHEAD", "HIGH", "d", 800, 0.01)],
    )
    d = rep.as_dict()
    assert d["session"] == "sess.jsonl"
    assert d["total_input"] == 1000
    assert d["phase"]["preread_input"] == 800
    assert d["findings"][0]["kind"] == "PRE_READ_OVERHEAD"
    assert d["by_model"]["claude-sonnet-4"] == 0.0123
