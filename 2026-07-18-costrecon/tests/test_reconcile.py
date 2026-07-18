"""Tests for the reconciliation engine."""

from costrecon.models import Estimate
from costrecon.reconcile import Reconciler, OVER_ESTIMATE, UNDER_ESTIMATE, UNESTIMATED, NO_ACTUAL, WITHIN_TOLERANCE


def _recon(actuals, estimates, threshold=5.0):
    return Reconciler(threshold).reconcile(actuals, [Estimate(k, v) for k, v in estimates.items()])


def test_within_tolerance_no_anomaly():
    r = _recon({"EC2": 10.0}, {"EC2": 10.0})
    v = r.by_key[0]
    assert v.classification == WITHIN_TOLERANCE
    assert v.anomaly is False
    assert v.pct == 0.0


def test_over_estimate_flags_anomaly():
    r = _recon({"EC2": 15.0}, {"EC2": 10.0})
    v = r.by_key[0]
    assert v.classification == OVER_ESTIMATE
    assert v.anomaly is True
    assert v.pct == 50.0


def test_under_estimate_flags_anomaly():
    r = _recon({"EC2": 9.0}, {"EC2": 10.0})
    v = r.by_key[0]
    assert v.classification == UNDER_ESTIMATE
    assert v.anomaly is True
    assert v.pct == -10.0


def test_boundary_at_threshold_is_within():
    # -5.0% is exactly at the 5% boundary -> WITHIN (<=), not an anomaly.
    r = _recon({"EC2": 9.5}, {"EC2": 10.0})
    v = r.by_key[0]
    assert v.pct == -5.0
    assert v.classification == WITHIN_TOLERANCE
    assert v.anomaly is False


def test_unestimated_spend_flagged():
    r = _recon({"S3": 20.0}, {"S3": 0.0})
    v = [x for x in r.by_key if x.key == "S3"][0]
    assert v.classification == UNESTIMATED
    assert v.anomaly is True


def test_no_actual_is_not_anomaly():
    r = _recon({"RDS": 0.0}, {"RDS": 5.0})
    v = r.by_key[0]
    assert v.classification == NO_ACTUAL
    assert v.anomaly is False


def test_unestimated_service_from_actuals():
    r = _recon({"EC2": 10.0, "Lambda": 4.0}, {"EC2": 10.0})
    assert "Lambda" in r.unestimated_services
    assert any(x.key == "Lambda" and x.anomaly for x in r.by_key)


def test_totals_and_anomaly_count():
    r = _recon({"EC2": 15.0, "S3": 2.0}, {"EC2": 10.0, "S3": 2.0})
    assert r.total_estimated == 12.0
    assert r.total_actual == 17.0
    assert r.anomalies  # EC2 over by 50%
    assert len(r.anomalies) == 1


def test_anomalies_sorted_first():
    r = _recon({"EC2": 15.0, "S3": 2.0, "RDS": 5.0}, {"EC2": 10.0, "S3": 2.0, "RDS": 5.0})
    assert r.by_key[0].anomaly is True
    assert all(x.anomaly for x in r.by_key[: len(r.anomalies)])
