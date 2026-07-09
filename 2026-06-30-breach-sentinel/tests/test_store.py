"""Tests for the SQLite store (persistence + idempotent inserts)."""

from breach_sentinel.models import Alert, BreachRecord, BreachType, Identity, Severity
from breach_sentinel.store import SentinelStore


def test_add_and_list_identity(clean_db):
    store = SentinelStore(clean_db)
    store.add_identity(Identity(iid="a", label="Alice", email="a@b.com"))
    ids = store.list_identities()
    assert len(ids) == 1
    assert ids[0].email == "a@b.com"


def test_breach_insert_is_idempotent(clean_db):
    store = SentinelStore(clean_db)
    rec = BreachRecord(
        bid="b1", source_id="s", identity_value="a@b.com", breach_type=BreachType.EMAIL, breach_name="X",
    )
    assert store.add_breaches([rec]) == 1
    assert store.add_breaches([rec]) == 0  # same bid, not re-added
    assert len(store.all_breaches()) == 1


def test_breaches_for_identity_case_insensitive(clean_db):
    store = SentinelStore(clean_db)
    rec = BreachRecord(bid="b1", source_id="s", identity_value="alice@example.com", breach_type=BreachType.EMAIL, breach_name="X")
    store.add_breaches([rec])
    found = store.breaches_for_identity("ALICE@Example.com")
    assert len(found) == 1


def test_alert_insert_idempotent(clean_db):
    store = SentinelStore(clean_db)
    a = Alert(aid="a1", iid="x", severity=Severity.HIGH, title="T", body="B")
    assert store.add_alerts([a]) == 1
    assert store.add_alerts([a]) == 0
    assert len(store.recent_alerts()) == 1
