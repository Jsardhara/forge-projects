"""Tests for AgentIAM — Audit Log."""

import pytest
from datetime import datetime, timezone, timedelta
from agentiam import AgentIAM, AuditLog


@pytest.fixture
def log():
    return AuditLog()


@pytest.fixture
def iam():
    return AgentIAM()


class TestRecord:
    def test_record_basic(self, log):
        event = log.record("agent-1", "read", "file.txt", "allow")
        assert event.agent_id == "agent-1"
        assert event.action == "read"
        assert event.resource == "file.txt"
        assert event.result == "allow"
        assert event.event_id.startswith("evt-")

    def test_record_with_details(self, log):
        event = log.record("agent-1", "write", "db", "deny", details={"reason": "no scope"})
        assert event.details["reason"] == "no scope"

    def test_record_with_credential(self, log):
        event = log.record("agent-1", "read", "api", "allow", credential_id="cred-123")
        assert event.credential_id == "cred-123"


class TestForAgent:
    def test_filter_by_agent(self, log):
        log.record("agent-1", "read", "a", "allow")
        log.record("agent-2", "read", "b", "allow")
        log.record("agent-1", "write", "c", "deny")
        events = log.for_agent("agent-1")
        assert len(events) == 2
        assert all(e.agent_id == "agent-1" for e in events)


class TestForAction:
    def test_filter_by_action(self, log):
        log.record("a1", "read", "x", "allow")
        log.record("a2", "write", "y", "allow")
        log.record("a3", "read", "z", "allow")
        events = log.for_action("read")
        assert len(events) == 2


class TestSince:
    def test_since(self, log):
        old_ts = datetime.now(timezone.utc) - timedelta(hours=1)
        log.record("a1", "read", "x", "allow")
        events = log.since(old_ts)
        assert len(events) == 1

    def test_since_future(self, log):
        future_ts = datetime.now(timezone.utc) + timedelta(hours=1)
        log.record("a1", "read", "x", "allow")
        events = log.since(future_ts)
        assert len(events) == 0


class TestAll:
    def test_all(self, log):
        log.record("a1", "read", "x", "allow")
        log.record("a2", "write", "y", "deny")
        assert len(log.all()) == 2


class TestCount:
    def test_count(self, log):
        assert log.count() == 0
        log.record("a1", "read", "x", "allow")
        assert log.count() == 1


class TestExportJson:
    def test_export(self, log):
        log.record("a1", "read", "x", "allow", details={"key": "val"})
        exported = log.export_json()
        assert "a1" in exported
        assert "read" in exported
        assert "val" in exported
