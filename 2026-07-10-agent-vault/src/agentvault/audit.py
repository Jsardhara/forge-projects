"""Tamper-evident audit trail for secret access.

Each entry is chained to the previous via SHA-256 of (prev_hash + canonical entry),
so any retroactive edit to an earlier record invalidates every subsequent hash.
No external dependencies.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AuditEntry:
    seq: int
    session_id: str
    action: str  # e.g. "resolve", "deny", "revoke", "egress-allow", "egress-deny"
    target: str  # secret id / host
    detail: str
    timestamp: datetime = field(default_factory=_now)
    prev_hash: str = "GENESIS"
    entry_hash: str = ""

    def canonical(self) -> str:
        """Stable string for hashing (timestamp is ISO + Z)."""
        ts = self.timestamp.astimezone(timezone.utc).isoformat()
        return json.dumps(
            {
                "seq": self.seq,
                "session_id": self.session_id,
                "action": self.action,
                "target": self.target,
                "detail": self.detail,
                "timestamp": ts,
                "prev_hash": self.prev_hash,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    def compute_hash(self) -> str:
        return hashlib.sha256(self.canonical().encode("utf-8")).hexdigest()


class AuditTrail:
    """Append-only, hash-chained audit log."""

    def __init__(self) -> None:
        self._entries: List[AuditEntry] = []
        self._prev_hash = "GENESIS"

    def record(
        self, session_id: str, action: str, target: str, detail: str
    ) -> AuditEntry:
        seq = len(self._entries) + 1
        entry = AuditEntry(
            seq=seq,
            session_id=session_id,
            action=action,
            target=target,
            detail=detail,
            prev_hash=self._prev_hash,
        )
        h = entry.compute_hash()
        entry = _with_hash(entry, h)
        self._entries.append(entry)
        self._prev_hash = h
        return entry

    def verify(self) -> bool:
        """True iff the whole chain is intact (no entry tampered)."""
        prev = "GENESIS"
        for e in self._entries:
            if e.prev_hash != prev:
                return False
            if e.entry_hash != e.compute_hash():
                return False
            if e.compute_hash() != _recompute(e):
                return False
            prev = e.entry_hash
        return True

    def tampered_at(self) -> Optional[int]:
        """Return the seq number of the first tampered entry, or None."""
        prev = "GENESIS"
        for e in self._entries:
            if e.prev_hash != prev or e.entry_hash != e.compute_hash():
                return e.seq
            prev = e.entry_hash
        return None

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries)

    @property
    def entries(self) -> List[AuditEntry]:
        return list(self._entries)


def _with_hash(entry: AuditEntry, h: str) -> AuditEntry:
    import dataclasses

    return dataclasses.replace(entry, entry_hash=h)


def _recompute(entry: AuditEntry) -> str:
    # recompute the hash from canonical (ignores stored entry_hash field)
    ts = entry.timestamp.astimezone(timezone.utc).isoformat()
    canon = json.dumps(
        {
            "seq": entry.seq,
            "session_id": entry.session_id,
            "action": entry.action,
            "target": entry.target,
            "detail": entry.detail,
            "timestamp": ts,
            "prev_hash": entry.prev_hash,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()
