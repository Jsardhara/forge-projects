"""Tests for idle / over-provisioned resource detection."""

from costrecon.idle import IdleDetector
from costrecon.models import ResourceUtilization


def _detect(rows, **kw):
    return IdleDetector(**kw).detect(rows)


def test_low_utilization_ec2_flagged_critical():
    rows = [ResourceUtilization("i-idle", "ec2", 1.0, 100.0)]
    r = _detect(rows)
    assert len(r.findings) == 1
    f = r.findings[0]
    assert f.severity == "CRITICAL"
    assert f.estimated_savings == 99.0


def test_healthy_utilization_not_flagged():
    rows = [ResourceUtilization("i-ok", "ec2", 50.0, 100.0)]
    r = _detect(rows)
    assert r.findings == []


def test_utilization_at_threshold_not_flagged():
    # exactly at 5.0% is NOT below the threshold -> not idle
    rows = [ResourceUtilization("i-edge", "ec2", 5.0, 100.0)]
    r = _detect(rows)
    assert r.findings == []


def test_unattached_ebs_flagged_full_savings():
    rows = [ResourceUtilization("vol-1", "ebs", None, 20.0, state="unattached")]
    r = _detect(rows)
    assert len(r.findings) == 1
    assert r.findings[0].estimated_savings == 20.0


def test_unassociated_eip_flagged():
    rows = [ResourceUtilization("eip-1", "eip", None, 5.0, state="available")]
    r = _detect(rows)
    assert len(r.findings) == 1
    assert r.findings[0].estimated_savings == 5.0


def test_stale_snapshot_flagged():
    rows = [ResourceUtilization("snap-1", "snapshot", None, 2.0, age_days=90.0)]
    r = _detect(rows)
    assert len(r.findings) == 1
    # wasted = (90-30)/90 = 0.6667 -> WARN
    assert r.findings[0].severity == "WARN"
    assert abs(r.findings[0].estimated_savings - 1.3334) < 0.001


def test_fresh_snapshot_not_flagged():
    rows = [ResourceUtilization("snap-2", "snapshot", None, 2.0, age_days=10.0)]
    r = _detect(rows)
    assert r.findings == []


def test_snapshot_without_age_skipped():
    rows = [ResourceUtilization("snap-3", "snapshot", None, 2.0)]
    r = _detect(rows)
    assert r.findings == []


def test_no_false_positive_for_unknown_type_no_state():
    rows = [ResourceUtilization("x-1", "other", None, 999.0)]
    r = _detect(rows)
    assert r.findings == []


def test_total_savings_summed():
    rows = [
        ResourceUtilization("i-idle", "ec2", 1.0, 100.0),
        ResourceUtilization("vol-1", "ebs", None, 20.0, state="unattached"),
        ResourceUtilization("eip-1", "eip", None, 5.0, state="available"),
        ResourceUtilization("i-ok", "ec2", 50.0, 100.0),
    ]
    r = _detect(rows)
    assert len(r.findings) == 3
    assert abs(r.total_savings - (99.0 + 20.0 + 5.0)) < 0.001


def test_min_cost_filter():
    rows = [ResourceUtilization("i-tiny", "ec2", 1.0, 0.001)]
    r = _detect(rows, min_cost=0.01)
    assert r.findings == []
