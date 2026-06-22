"""Audit trail generator — creates tamper-evident audit logs."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from predictguard.models import AuditEntry


def _hash_entry(entry: AuditEntry) -> str:
    """Create SHA-256 hash of audit entry for integrity verification."""
    data = f"{entry.eid}|{entry.event_type}|{entry.actor}|{entry.description}|{entry.timestamp.isoformat()}"
    return hashlib.sha256(data.encode()).hexdigest()


class AuditTrail:
    """Generates and manages tamper-evident audit trails."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"AUD-{self._counter:06d}"

    def log(
        self,
        event_type: str,
        actor: str,
        description: str,
        metadata: dict | None = None,
    ) -> AuditEntry:
        """Log an audit event."""
        entry = AuditEntry(
            eid=self._next_id(),
            event_type=event_type,
            actor=actor,
            description=description,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        entry.data_hash = _hash_entry(entry)
        self._entries.append(entry)
        return entry

    def get_entries(
        self,
        event_type: str | None = None,
        actor: str | None = None,
        since: datetime | None = None,
    ) -> list[AuditEntry]:
        """Get audit entries, optionally filtered."""
        results = list(self._entries)
        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]
        if actor is not None:
            results = [e for e in results if e.actor == actor]
        if since is not None:
            results = [e for e in results if e.timestamp >= since]
        return results

    def verify_integrity(self) -> tuple[bool, list[str]]:
        """Verify integrity of all audit entries.

        Returns (all_valid, list_of_failed_ids).
        """
        failed: list[str] = []
        for entry in self._entries:
            expected = _hash_entry(entry)
            if entry.data_hash != expected:
                failed.append(entry.eid)
        return len(failed) == 0, failed

    def export_json(self) -> str:
        """Export audit trail as JSON string."""
        data = []
        for e in self._entries:
            data.append({
                "id": e.eid,
                "event_type": e.event_type,
                "actor": e.actor,
                "description": e.description,
                "timestamp": e.timestamp.isoformat(),
                "metadata": e.metadata,
                "data_hash": e.data_hash,
            })
        return json.dumps(data, indent=2)

    def export_csv(self) -> str:
        """Export audit trail as CSV string."""
        lines = ["id,event_type,actor,description,timestamp,data_hash"]
        for e in self._entries:
            desc = e.description.replace('"', '""')
            lines.append(
                f'{e.eid},{e.event_type},{e.actor},"{desc}",{e.timestamp.isoformat()},{e.data_hash}'
            )
        return "\n".join(lines)

    @property
    def entry_count(self) -> int:
        return len(self._entries)
