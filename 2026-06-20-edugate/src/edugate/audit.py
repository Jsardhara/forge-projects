"""Audit logging for AI access events."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


@dataclasses.dataclass
class AuditEvent:
    """A single audit event."""
    event_id: str
    timestamp: str
    student_id: str
    student_name: str
    grade: int
    tool_name: str
    decision: str
    reason: str
    teacher_id: str | None
    ip_hash: str | None  # SHA-256 hashed IP for privacy


class AuditLogger:
    """Append-only audit log for AI access events."""

    def __init__(self, log_path: Path | None = None) -> None:
        self._events: list[AuditEvent] = []
        self._log_path = log_path

    def log(
        self,
        student_id: str,
        student_name: str,
        grade: int,
        tool_name: str,
        decision: str,
        reason: str,
        teacher_id: str | None = None,
        ip_address: str | None = None,
    ) -> AuditEvent:
        """Log an access event."""
        event_id = self._generate_id(student_id, tool_name)
        ip_hash = self._hash_ip(ip_address) if ip_address else None
        timestamp = datetime.now(timezone.utc).isoformat()

        event = AuditEvent(
            event_id=event_id,
            timestamp=timestamp,
            student_id=student_id,
            student_name=student_name,
            grade=grade,
            tool_name=tool_name,
            decision=decision,
            reason=reason,
            teacher_id=teacher_id,
            ip_hash=ip_hash,
        )
        self._events.append(event)
        return event

    @property
    def events(self) -> list[AuditEvent]:
        """Return a copy of all events."""
        return list(self._events)

    def filter_by_student(self, student_id: str) -> list[AuditEvent]:
        """Get all events for a specific student."""
        return [e for e in self._events if e.student_id == student_id]

    def filter_by_decision(self, decision: str) -> list[AuditEvent]:
        """Get all events with a specific decision."""
        return [e for e in self._events if e.decision == decision]

    def filter_by_grade(self, grade: int) -> list[AuditEvent]:
        """Get all events for a specific grade."""
        return [e for e in self._events if e.grade == grade]

    def filter_by_date(self, date: str) -> list[AuditEvent]:
        """Get all events for a specific date (YYYY-MM-DD)."""
        return [e for e in self._events if e.timestamp[:10] == date]

    def summary(self) -> dict:
        """Get a summary of all logged events."""
        total = len(self._events)
        allowed = sum(1 for e in self._events if e.decision == "allow")
        denied = sum(1 for e in self._events if e.decision == "deny")
        supervised = sum(1 for e in self._events if "supervis" in e.reason.lower())
        unique_students = len(set(e.student_id for e in self._events))
        unique_tools = len(set(e.tool_name for e in self._events))
        return {
            "total_events": total,
            "allowed": allowed,
            "denied": denied,
            "supervised": supervised,
            "unique_students": unique_students,
            "unique_tools": unique_tools,
        }

    def export_json(self) -> str:
        """Export all events as JSON."""
        data = [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp,
                "student_id": e.student_id,
                "student_name": e.student_name,
                "grade": e.grade,
                "tool_name": e.tool_name,
                "decision": e.decision,
                "reason": e.reason,
                "teacher_id": e.teacher_id,
            }
            for e in self._events
        ]
        return json.dumps(data, indent=2)

    def _generate_id(self, student_id: str, tool_name: str) -> str:
        raw = f"{student_id}-{tool_name}-{datetime.now(timezone.utc).isoformat()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _hash_ip(self, ip: str) -> str:
        return hashlib.sha256(ip.encode()).hexdigest()[:12]
