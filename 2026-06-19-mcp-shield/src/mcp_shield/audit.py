"""Audit logging for MCP tool calls with structured events and severity levels."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class AuditSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

    @classmethod
    def from_score(cls, risk_score: float) -> "AuditSeverity":
        if risk_score >= 0.7:
            return cls.CRITICAL
        elif risk_score >= 0.4:
            return cls.WARNING
        return cls.INFO


@dataclass
class AuditEvent:
    """A single MCP tool-call audit event."""
    event_id: str
    timestamp: str
    agent_id: str
    tool_name: str
    server_id: str
    arguments_hash: str
    action: str
    decision: str
    risk_score: float
    severity: str
    reason: str = ""
    session_id: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """
    Append-only audit logger for MCP tool calls.

    Records every tool-call attempt with agent identity, tool name,
    server ID, policy decision, and risk score. Supports filtering,
    JSON export, and integrity hashing.
    """

    def __init__(self, events: Optional[list[AuditEvent]] = None):
        self._events: list[AuditEvent] = events or []

    @property
    def events(self) -> list[AuditEvent]:
        return list(self._events)

    @property
    def count(self) -> int:
        return len(self._events)

    def log(
        self,
        *,
        agent_id: str,
        tool_name: str,
        server_id: str,
        arguments: dict,
        action: str,
        decision: str,
        risk_score: float = 0.0,
        reason: str = "",
        session_id: str = "",
        metadata: Optional[dict] = None,
    ) -> AuditEvent:
        """Record a tool-call audit event."""
        ts = datetime.now(timezone.utc).isoformat()
        args_hash = self._hash_args(arguments)
        severity = AuditSeverity.from_score(risk_score)
        event_id = self._generate_id(agent_id, tool_name, ts)

        event = AuditEvent(
            event_id=event_id,
            timestamp=ts,
            agent_id=agent_id,
            tool_name=tool_name,
            server_id=server_id,
            arguments_hash=args_hash,
            action=action,
            decision=decision,
            risk_score=risk_score,
            severity=severity.value,
            reason=reason,
            session_id=session_id,
            metadata=metadata or {},
        )
        self._events.append(event)
        return event

    def filter_by_agent(self, agent_id: str) -> list[AuditEvent]:
        return [e for e in self._events if e.agent_id == agent_id]

    def filter_by_severity(self, severity: str) -> list[AuditEvent]:
        return [e for e in self._events if e.severity == severity]

    def filter_by_tool(self, tool_name: str) -> list[AuditEvent]:
        return [e for e in self._events if e.tool_name == tool_name]

    def filter_by_decision(self, decision: str) -> list[AuditEvent]:
        return [e for e in self._events if e.decision == decision]

    def filter_by_time_range(
        self, start: datetime, end: datetime
    ) -> list[AuditEvent]:
        results = []
        for e in self._events:
            ts = datetime.fromisoformat(e.timestamp)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if start <= ts <= end:
                results.append(e)
        return results

    def get_critical_events(self) -> list[AuditEvent]:
        return self.filter_by_severity(AuditSeverity.CRITICAL.value)

    def summary(self) -> dict:
        """Return aggregate statistics."""
        if not self._events:
            return {
                "total": 0,
                "by_decision": {},
                "by_severity": {},
                "by_agent": {},
                "by_tool": {},
                "avg_risk": 0.0,
            }

        by_decision: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        by_agent: dict[str, int] = {}
        by_tool: dict[str, int] = {}
        total_risk = 0.0

        for e in self._events:
            by_decision[e.decision] = by_decision.get(e.decision, 0) + 1
            by_severity[e.severity] = by_severity.get(e.severity, 0) + 1
            by_agent[e.agent_id] = by_agent.get(e.agent_id, 0) + 1
            by_tool[e.tool_name] = by_tool.get(e.tool_name, 0) + 1
            total_risk += e.risk_score

        return {
            "total": self.count,
            "by_decision": by_decision,
            "by_severity": by_severity,
            "by_agent": by_agent,
            "by_tool": by_tool,
            "avg_risk": round(total_risk / self.count, 3),
        }

    def export_json(self, path: Path) -> int:
        """Export all events to a JSON file. Returns number of events written."""
        data = [e.to_dict() for e in self._events]
        path.write_text(json.dumps(data, indent=2, default=str))
        return len(data)

    def _hash_args(self, arguments: dict) -> str:
        raw = json.dumps(arguments, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _generate_id(self, agent_id: str, tool_name: str, ts: str) -> str:
        raw = f"{agent_id}:{tool_name}:{ts}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]
