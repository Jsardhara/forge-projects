"""Tests for PredictGuard audit trail."""

from datetime import datetime, timezone
from predictguard.audit import AuditTrail


class TestAuditTrail:
    def test_log_entry(self):
        trail = AuditTrail()
        entry = trail.log("trade", "alice", "Buy Yes @ 0.62")
        assert entry.eid == "AUD-000001"
        assert entry.event_type == "trade"
        assert entry.actor == "alice"
        assert entry.data_hash != ""

    def test_multiple_entries(self):
        trail = AuditTrail()
        trail.log("system", "predictguard", "Init")
        trail.log("trade", "alice", "Buy")
        trail.log("trade", "bob", "Sell")
        assert trail.entry_count == 3

    def test_filter_by_event_type(self):
        trail = AuditTrail()
        trail.log("system", "predictguard", "Init")
        trail.log("trade", "alice", "Buy")
        trail.log("trade", "bob", "Sell")
        trades = trail.get_entries(event_type="trade")
        assert len(trades) == 2

    def test_filter_by_actor(self):
        trail = AuditTrail()
        trail.log("trade", "alice", "Buy")
        trail.log("trade", "bob", "Sell")
        trail.log("trade", "alice", "Sell")
        alice_entries = trail.get_entries(actor="alice")
        assert len(alice_entries) == 2

    def test_filter_by_since(self):
        trail = AuditTrail()
        old = datetime(2026, 1, 1, tzinfo=timezone.utc)
        new = datetime.now(timezone.utc)
        trail.log("system", "predictguard", "New entry", metadata={"ts": new.isoformat()})
        # Both entries are "new" — just verify filtering doesn't crash
        entries = trail.get_entries(since=old)
        assert len(entries) >= 1

    def test_verify_integrity_valid(self):
        trail = AuditTrail()
        trail.log("system", "predictguard", "Init")
        trail.log("trade", "alice", "Buy")
        valid, failed = trail.verify_integrity()
        assert valid is True
        assert len(failed) == 0

    def test_export_json(self):
        trail = AuditTrail()
        trail.log("system", "predictguard", "Init", metadata={"version": "0.1.0"})
        json_str = trail.export_json()
        assert "AUD-000001" in json_str
        assert "predictguard" in json_str
        data = __import__('json').loads(json_str)
        assert len(data) == 1
        assert data[0]["event_type"] == "system"

    def test_export_csv(self):
        trail = AuditTrail()
        trail.log("trade", "alice", "Buy Yes")
        csv_str = trail.export_csv()
        lines = csv_str.strip().split("\n")
        assert len(lines) == 2  # header + 1 entry
        assert "id,event_type,actor" in lines[0]
        assert "alice" in lines[1]

    def test_metadata(self):
        trail = AuditTrail()
        entry = trail.log("trade", "alice", "Buy", metadata={"price": 0.62, "qty": 100})
        assert entry.metadata["price"] == 0.62
        assert entry.metadata["qty"] == 100

    def test_hash_uniqueness(self):
        trail = AuditTrail()
        e1 = trail.log("trade", "alice", "Buy")
        e2 = trail.log("trade", "bob", "Sell")
        assert e1.data_hash != e2.data_hash
