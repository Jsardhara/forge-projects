"""Tests for data models and the bid/id determinism (dedupe correctness)."""

from datetime import datetime, timezone

import pytest

from breach_sentinel.models import (
    Alert,
    BreachRecord,
    BreachType,
    ExposureScore,
    Identity,
    Severity,
)


def test_breach_type_sensitivity_weights_monotonic():
    from breach_sentinel.models import SENSITIVITY_WEIGHT
    assert SENSITIVITY_WEIGHT[BreachType.SSN] > SENSITIVITY_WEIGHT[BreachType.EMAIL]
    assert SENSITIVITY_WEIGHT[BreachType.PASSPORT] >= SENSITIVITY_WEIGHT[BreachType.PASSWORD]


def test_identity_search_keys_omits_blanks():
    ident = Identity(iid="x", label="X", email="a@b.com", phone=None, ssn="", passport=None)
    assert ident.search_keys() == ["a@b.com"]


def test_breach_record_bid_is_deterministic():
    b1 = BreachRecord.make_bid("src", "Alice@Example.com", BreachType.EMAIL, "Adobe 2013")
    b2 = BreachRecord.make_bid("src", "alice@example.com", BreachType.EMAIL, "Adobe 2013")
    assert b1 == b2  # case-insensitive dedupe


def test_breach_record_bid_differs_by_source():
    b1 = BreachRecord.make_bid("src1", "a@b.com", BreachType.EMAIL, "X")
    b2 = BreachRecord.make_bid("src2", "a@b.com", BreachType.EMAIL, "X")
    assert b1 != b2


def test_severity_from_rank_bounds():
    assert Severity.from_rank(-5) == Severity.INFO
    assert Severity.from_rank(99) == Severity.CRITICAL
    assert Severity.from_rank(4) == Severity.CRITICAL


def test_alert_aid_deterministic():
    a1 = Alert.make_aid("alice", "Breach exposure HIGH: Alice")
    a2 = Alert.make_aid("alice", "Breach exposure HIGH: Alice")
    assert a1 == a2


def test_exposure_score_frozen():
    s = ExposureScore(iid="x", score=10, severity=Severity.LOW, record_count=1, critical_types=[])
    with pytest.raises(Exception):
        s.score = 99


def test_breach_record_frozen():
    r = BreachRecord(
        bid="b", source_id="s", identity_value="v", breach_type=BreachType.EMAIL, breach_name="n",
        added_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    with pytest.raises(Exception):
        r.breach_name = "other"
