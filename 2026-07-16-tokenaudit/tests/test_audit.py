from tokenaudit.models import CostReport, WasteFinding
from tokenaudit.audit import recommendations


def test_recommendation_for_preread():
    rep = CostReport(
        session="s", agent="claude-code", total_input=10000,
        findings=[WasteFinding("PRE_READ_OVERHEAD", "HIGH", "d", 10000, 0.03)],
    )
    recs = recommendations(rep)
    titles = [r.title for r in recs]
    assert "Trim the init/system context" in titles
    pre = next(r for r in recs if r.title == "Trim the init/system context")
    assert pre.potential_savings_pct == 0.5


def test_recommendation_no_waste():
    rep = CostReport(session="s", agent="generic", total_cost=0.01, findings=[])
    recs = recommendations(rep)
    assert any(r.title == "No major waste detected" for r in recs)
    # cost below the routing tip threshold -> no extra routing rec
    assert not any("Route cheap tasks" in r.title for r in recs)


def test_recommendation_routing_tip_when_costly():
    rep = CostReport(session="s", agent="generic", total_cost=0.20, findings=[])
    recs = recommendations(rep)
    assert any("Route cheap tasks" in r.title for r in recs)
