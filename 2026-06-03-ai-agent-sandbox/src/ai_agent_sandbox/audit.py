"""Audit Logger — Centralized audit trail for all agent actions.

Records API key access, network egress, and filesystem operations
into a single queryable log. Supports exporting to JSON for compliance.
"""

from __future__ import annotations

import json
import time
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AuditEntry:
    """A single audit log entry."""
    timestamp: float
    agent_id: str
    category: str  # "key_access", "network", "filesystem", "system"
    action: str
    detail: str
    allowed: bool
    severity: str = "info"  # "info", "warning", "critical"


class AuditLogger:
    """Centralized audit logging for the AI Agent Sandbox.

    Collects events from all sandbox subsystems into a single
    queryable, exportable log.

    Usage:
        logger = AuditLogger()
        logger.log("network", "https://evil.com/data", False, severity="critical")
        violations = logger.get_violations()
        logger.export_json("/tmp/audit.json")
    """

    def __init__(self, agent_id: str = "default") -> None:
        self._agent_id = agent_id
        self._entries: list[AuditEntry] = []
        self._lock = threading.Lock()

    def log(
        self,
        category: str,
        action: str,
        allowed: bool,
        detail: str = "",
        severity: str = "info",
        agent_id: str = "",
    ) -> AuditEntry:
        """Record an audit event."""
        entry = AuditEntry(
            timestamp=time.time(),
            agent_id=agent_id or self._agent_id,
            category=category,
            action=action,
            detail=detail,
            allowed=allowed,
            severity=severity,
        )
        with self._lock:
            self._entries.append(entry)
        return entry

    def get_entries(
        self,
        category: str = "",
        severity: str = "",
        since: float = 0,
    ) -> list[AuditEntry]:
        """Get audit entries, optionally filtered."""
        with self._lock:
            entries = list(self._entries)
        if category:
            entries = [e for e in entries if e.category == category]
        if severity:
            entries = [e for e in entries if e.severity == severity]
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        return entries

    def get_violations(self) -> list[AuditEntry]:
        """Get all denied/blocked actions."""
        with self._lock:
            return [e for e in self._entries if not e.allowed]

    def get_critical(self) -> list[AuditEntry]:
        """Get all critical-severity entries."""
        return self.get_entries(severity="critical")

    def export_json(self, path: str) -> int:
        """Export the audit log to JSON. Returns number of entries written."""
        entries = self.get_entries()
        data = [
            {
                "timestamp": e.timestamp,
                "datetime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(e.timestamp)),
                "agent_id": e.agent_id,
                "category": e.category,
                "action": e.action,
                "detail": e.detail,
                "allowed": e.allowed,
                "severity": e.severity,
            }
            for e in entries
        ]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return len(data)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    @property
    def violation_count(self) -> int:
        return len(self.get_violations())

    def summary(self) -> dict:
        """Return a summary of the audit log."""
        with self._lock:
            entries = list(self._entries)
        return {
            "total_entries": len(entries),
            "violations": sum(1 for e in entries if not e.allowed),
            "critical": sum(1 for e in entries if e.severity == "critical"),
            "by_category": {
                cat: sum(1 for e in entries if e.category == cat)
                for cat in set(e.category for e in entries)
            },
        }
