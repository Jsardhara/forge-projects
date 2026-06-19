"""Tests for mcp_shield.audit module."""

import json
import pytest
from datetime import datetime, timezone

from mcp_shield.audit import AuditLogger, AuditEvent, AuditSeverity


class TestAuditSeverity:
    def test_from_score_critical(self):
        assert AuditSeverity.from_score(0.7) == AuditSeverity.CRITICAL
        assert AuditSeverity.from_score(1.0) == AuditSeverity.CRITICAL

    def test_from_score_warning(self):
        assert AuditSeverity.from_score(0.4) == AuditSeverity.WARNING
        assert AuditSeverity.from_score(0.69) == AuditSeverity.WARNING

    def test_from_score_info(self):
        assert AuditSeverity.from_score(0.0) == AuditSeverity.INFO
        assert AuditSeverity.from_score(0.39) == AuditSeverity.INFO


class TestAuditEvent:
    def test_to_dict(self):
        event = AuditEvent(
            event_id="abc123",
            timestamp="2026-06-19T00:00:00+00:00",
            agent_id="agent-001",
            tool_name="read_file",
            server_id="server-a",
            arguments_hash="deadbeef",
            action="tool_call",
            decision="allow",
            risk_score=0.1,
            severity="info",
        )
        d = event.to_dict()
        assert d["event_id"] == "abc123"
        assert d["agent_id"] == "agent-001"
        assert d["tool_name"] == "read_file"

    def test_to_json(self):
        event = AuditEvent(
            event_id="abc",
            timestamp="2026-06-19T00:00:00+00:00",
            agent_id="a",
            tool_name="t",
            server_id="s",
            arguments_hash="h",
            action="tool_call",
            decision="allow",
            risk_score=0.0,
            severity="info",
        )
        raw = event.to_json()
        parsed = json.loads(raw)
        assert parsed["event_id"] == "abc"


class TestAuditLogger:
    def _make_logger(self):
        return AuditLogger()

    def test_log_basic(self):
        logger = self._make_logger()
        event = logger.log(
            agent_id="agent-001",
            tool_name="read_file",
            server_id="server-a",
            arguments={"path": "/tmp/test.txt"},
            action="tool_call",
            decision="allow",
        )
        assert event.agent_id == "agent-001"
        assert event.tool_name == "read_file"
        assert event.decision == "allow"
        assert event.risk_score == 0.0
        assert event.severity == "info"

    def test_log_with_risk(self):
        logger = self._make_logger()
        event = logger.log(
            agent_id="agent-001",
            tool_name="exec",
            server_id="server-a",
            arguments={"command": "sudo rm -rf /"},
            action="tool_call",
            decision="deny",
            risk_score=0.95,
        )
        assert event.severity == "critical"

    def test_count(self):
        logger = self._make_logger()
        assert logger.count == 0
        for i in range(5):
            logger.log(
                agent_id="a", tool_name="t", server_id="s",
                arguments={}, action="tool_call", decision="allow",
            )
        assert logger.count == 5

    def test_filter_by_agent(self):
        logger = self._make_logger()
        logger.log(agent_id="a1", tool_name="t", server_id="s", arguments={}, action="tool_call", decision="allow")
        logger.log(agent_id="a2", tool_name="t", server_id="s", arguments={}, action="tool_call", decision="allow")
        logger.log(agent_id="a1", tool_name="t2", server_id="s", arguments={}, action="tool_call", decision="deny")
        assert len(logger.filter_by_agent("a1")) == 2
        assert len(logger.filter_by_agent("a2")) == 1

    def test_filter_by_severity(self):
        logger = self._make_logger()
        logger.log(agent_id="a", tool_name="t", server_id="s", arguments={}, action="tool_call", decision="allow", risk_score=0.1)
        logger.log(agent_id="a", tool_name="t", server_id="s", arguments={}, action="tool_call", decision="deny", risk_score=0.9)
        assert len(logger.filter_by_severity("critical")) == 1
        assert len(logger.filter_by_severity("info")) == 1

    def test_filter_by_tool(self):
        logger = self._make_logger()
        logger.log(agent_id="a", tool_name="read", server_id="s", arguments={}, action="tool_call", decision="allow")
        logger.log(agent_id="a", tool_name="write", server_id="s", arguments={}, action="tool_call", decision="allow")
        assert len(logger.filter_by_tool("read")) == 1

    def test_filter_by_decision(self):
        logger = self._make_logger()
        logger.log(agent_id="a", tool_name="t", server_id="s", arguments={}, action="tool_call", decision="allow")
        logger.log(agent_id="a", tool_name="t", server_id="s", arguments={}, action="tool_call", decision="deny")
        assert len(logger.filter_by_decision("deny")) == 1

    def test_filter_by_time_range(self):
        logger = self._make_logger()
        logger.log(agent_id="a", tool_name="t", server_id="s", arguments={}, action="tool_call", decision="allow")
        now = datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59)
        assert len(logger.filter_by_time_range(start, end)) == 1

    def test_get_critical_events(self):
        logger = self._make_logger()
        logger.log(agent_id="a", tool_name="t", server_id="s", arguments={}, action="tool_call", decision="allow", risk_score=0.1)
        logger.log(agent_id="a", tool_name="t", server_id="s", arguments={}, action="tool_call", decision="deny", risk_score=0.95)
        critical = logger.get_critical_events()
        assert len(critical) == 1
        assert critical[0].risk_score == 0.95

    def test_summary_empty(self):
        logger = self._make_logger()
        s = logger.summary()
        assert s["total"] == 0
        assert s["avg_risk"] == 0.0

    def test_summary_with_events(self):
        logger = self._make_logger()
        logger.log(agent_id="a1", tool_name="read", server_id="s", arguments={}, action="tool_call", decision="allow", risk_score=0.1)
        logger.log(agent_id="a1", tool_name="exec", server_id="s", arguments={}, action="tool_call", decision="deny", risk_score=0.9)
        logger.log(agent_id="a2", tool_name="read", server_id="s", arguments={}, action="tool_call", decision="allow", risk_score=0.1)
        s = logger.summary()
        assert s["total"] == 3
        assert s["by_decision"]["allow"] == 2
        assert s["by_decision"]["deny"] == 1
        assert s["by_agent"]["a1"] == 2
        assert s["by_agent"]["a2"] == 1
        assert s["by_tool"]["read"] == 2
        assert s["by_tool"]["exec"] == 1
        assert s["avg_risk"] == pytest.approx(0.367, abs=0.01)

    def test_export_json(self, tmp_path):
        logger = self._make_logger()
        logger.log(agent_id="a", tool_name="t", server_id="s", arguments={}, action="tool_call", decision="allow")
        out = tmp_path / "audit.json"
        count = logger.export_json(out)
        assert count == 1
        data = json.loads(out.read_text())
        assert len(data) == 1
        assert data[0]["agent_id"] == "a"

    def test_arguments_hashing(self):
        logger = self._make_logger()
        e1 = logger.log(agent_id="a", tool_name="t", server_id="s", arguments={"x": 1}, action="tool_call", decision="allow")
        e2 = logger.log(agent_id="a", tool_name="t", server_id="s", arguments={"x": 1}, action="tool_call", decision="allow")
        e3 = logger.log(agent_id="a", tool_name="t", server_id="s", arguments={"x": 2}, action="tool_call", decision="allow")
        assert e1.arguments_hash == e2.arguments_hash
        assert e1.arguments_hash != e3.arguments_hash

    def test_events_returns_copy(self):
        logger = self._make_logger()
        logger.log(agent_id="a", tool_name="t", server_id="s", arguments={}, action="tool_call", decision="allow")
        events = logger.events
        events.clear()
        assert logger.count == 1  # internal list not affected
