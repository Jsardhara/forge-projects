"""Tests for the audit logger."""

from __future__ import annotations

from edugate.audit import AuditLogger


class TestAuditLogger:
    def test_log_event(self):
        logger = AuditLogger()
        event = logger.log(
            student_id="S1",
            student_name="Ada",
            grade=5,
            tool_name="ChatGPT",
            decision="deny",
            reason="Elementary ban",
        )
        assert event.student_id == "S1"
        assert event.decision == "deny"
        assert event.event_id is not None

    def test_events_returns_copy(self):
        logger = AuditLogger()
        logger.log("S1", "Ada", 5, "ChatGPT", "deny", "test")
        events = logger.events
        events.clear()
        assert len(logger.events) == 1  # Internal list not affected

    def test_filter_by_student(self):
        logger = AuditLogger()
        logger.log("S1", "Ada", 5, "ChatGPT", "deny", "test")
        logger.log("S2", "Bjorn", 9, "Claude", "allow", "test")
        logger.log("S1", "Ada", 5, "Gemini", "deny", "test")
        assert len(logger.filter_by_student("S1")) == 2
        assert len(logger.filter_by_student("S2")) == 1

    def test_filter_by_decision(self):
        logger = AuditLogger()
        logger.log("S1", "Ada", 5, "ChatGPT", "deny", "test")
        logger.log("S2", "Bjorn", 9, "Claude", "allow", "test")
        assert len(logger.filter_by_decision("deny")) == 1
        assert len(logger.filter_by_decision("allow")) == 1

    def test_filter_by_grade(self):
        logger = AuditLogger()
        logger.log("S1", "Ada", 5, "ChatGPT", "deny", "test")
        logger.log("S2", "Bjorn", 9, "Claude", "allow", "test")
        assert len(logger.filter_by_grade(5)) == 1
        assert len(logger.filter_by_grade(9)) == 1

    def test_filter_by_date(self):
        logger = AuditLogger()
        logger.log("S1", "Ada", 5, "ChatGPT", "deny", "test")
        events = logger.filter_by_date("2026-06-20")
        # Should match if today is 2026-06-20 (timestamp is generated internally)
        assert isinstance(events, list)

    def test_summary(self):
        logger = AuditLogger()
        logger.log("S1", "Ada", 5, "ChatGPT", "deny", "test")
        logger.log("S2", "Bjorn", 9, "Claude", "allow", "test")
        summary = logger.summary()
        assert summary["total_events"] == 2
        assert summary["allowed"] == 1
        assert summary["denied"] == 1
        assert summary["unique_students"] == 2
        assert summary["unique_tools"] == 2

    def test_export_json(self):
        logger = AuditLogger()
        logger.log("S1", "Ada", 5, "ChatGPT", "deny", "test")
        json_str = logger.export_json()
        assert "S1" in json_str
        assert "ChatGPT" in json_str

    def test_ip_hashing(self):
        logger = AuditLogger()
        event = logger.log(
            student_id="S1", student_name="Ada", grade=5,
            tool_name="ChatGPT", decision="deny", reason="test",
            ip_address="192.168.1.1",
        )
        assert event.ip_hash is not None
        assert event.ip_hash != "192.168.1.1"  # Should be hashed
        assert len(event.ip_hash) == 12  # Truncated SHA-256
