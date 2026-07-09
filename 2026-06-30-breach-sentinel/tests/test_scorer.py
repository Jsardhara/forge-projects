"""Tests for exposure scoring + alerting thresholds."""

from datetime import datetime, timezone

from breach_sentinel.alerting import build_alerts
from breach_sentinel.models import BreachRecord, BreachType, Identity, Severity
from breach_sentinel.scorer import score_exposure


def _rec(value, btype, name, date=None, count=None):
    return BreachRecord(
        bid=BreachRecord.make_bid("s", value, btype, name),
        source_id="s", identity_value=value, breach_type=btype, breach_name=name,
        breach_date=date, password_pwned_count=count,
        added_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_score_zero_for_no_records():
    s = score_exposure("x", [])
    assert s.score == 0
    assert s.severity == Severity.INFO


def test_score_email_only_low():
    s = score_exposure("x", [_rec("a@b.com", BreachType.EMAIL, "Adobe", datetime(2013, 10, 4, tzinfo=timezone.utc))])
    assert Severity.LOW.value == s.severity.value
    assert s.score > 0


def test_identity_document_drives_high():
    recs = [
        _rec("c@bank.com", BreachType.SSN, "Nefos", datetime(2026, 6, 29, tzinfo=timezone.utc)),
        _rec("c@bank.com", BreachType.PASSPORT, "Nefos", datetime(2026, 6, 29, tzinfo=timezone.utc)),
    ]
    s = score_exposure("c", recs)
    assert Severity.CRITICAL.value == s.severity.value
    assert BreachType.SSN in s.critical_types
    assert s.latest_breach.year == 2026


def test_recent_breach_bonus():
    recent = score_exposure("x", [_rec("a@b.com", BreachType.EMAIL, "X", datetime(2026, 7, 1, tzinfo=timezone.utc))])
    old = score_exposure("x", [_rec("a@b.com", BreachType.EMAIL, "X", datetime(2013, 1, 1, tzinfo=timezone.utc))])
    assert recent.score > old.score


def test_alert_fires_for_identity_document():
    ident = Identity(iid="carol", label="Carol", email="carol@bank.com", ssn="123-45-6789")
    recs = [_rec("carol@bank.com", BreachType.SSN, "Nefos", datetime(2026, 6, 29, tzinfo=timezone.utc))]
    alerts = build_alerts(ident, recs)
    assert len(alerts) == 1
    assert alerts[0].severity.rank >= Severity.HIGH.rank


def test_no_alert_when_clean():
    ident = Identity(iid="dave", label="Dave", email="dave@clean.com")
    alerts = build_alerts(ident, [])
    assert alerts == []
