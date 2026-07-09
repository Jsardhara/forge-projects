"""SQLite-backed persistence for BreachSentinel.

Stores identities, breach records (deduped by bid), and alerts. Designed so
repeated scans are idempotent: inserting the same breach record twice keeps a
single row. All writes are append-style for audit integrity.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from breach_sentinel.models import (
    Alert,
    BreachRecord,
    Identity,
    ScanResult,
)


def _dt_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _dt_parse(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class SentinelStore:
    def __init__(self, db_path: str = "breach_sentinel.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS identities (
                    iid TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    passport TEXT,
                    ssn TEXT,
                    note TEXT
                );
                CREATE TABLE IF NOT EXISTS breaches (
                    bid TEXT PRIMARY KEY,
                    source_id TEXT,
                    identity_value TEXT,
                    breach_type TEXT,
                    breach_name TEXT,
                    breach_date TEXT,
                    added_at TEXT,
                    description TEXT,
                    password_pwned_count INTEGER
                );
                CREATE TABLE IF NOT EXISTS alerts (
                    aid TEXT PRIMARY KEY,
                    iid TEXT,
                    severity TEXT,
                    title TEXT,
                    body TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS scans (
                    sid INTEGER PRIMARY KEY AUTOINCREMENT,
                    iid TEXT,
                    score INTEGER,
                    severity TEXT,
                    record_count INTEGER,
                    scanned_at TEXT
                );
                """
            )

    # --- identities ---
    def add_identity(self, ident: Identity) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO identities
                   (iid, label, email, phone, passport, ssn, note)
                   VALUES (?,?,?,?,?,?,?)""",
                (ident.iid, ident.label, ident.email, ident.phone,
                 ident.passport, ident.ssn, ident.note),
            )

    def get_identity(self, iid: str) -> Optional[Identity]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM identities WHERE iid=?", (iid,)).fetchone()
        if not row:
            return None
        return Identity(
            iid=row["iid"], label=row["label"], email=row["email"],
            phone=row["phone"], passport=row["passport"], ssn=row["ssn"],
            note=row["note"],
        )

    def list_identities(self) -> list[Identity]:
        out: list[Identity] = []
        with self._conn() as c:
            for row in c.execute("SELECT * FROM identities ORDER BY label"):
                out.append(Identity(
                    iid=row["iid"], label=row["label"], email=row["email"],
                    phone=row["phone"], passport=row["passport"], ssn=row["ssn"],
                    note=row["note"],
                ))
        return out

    # --- breaches ---
    def add_breaches(self, records: Iterable[BreachRecord]) -> int:
        added = 0
        with self._conn() as c:
            for r in records:
                cur = c.execute("SELECT 1 FROM breaches WHERE bid=?", (r.bid,)).fetchone()
                if cur:
                    continue
                c.execute(
                    """INSERT INTO breaches
                       (bid, source_id, identity_value, breach_type, breach_name,
                        breach_date, added_at, description, password_pwned_count)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (r.bid, r.source_id, r.identity_value, r.breach_type.value,
                     r.breach_name, _dt_iso(r.breach_date), _dt_iso(r.added_at),
                     r.description, r.password_pwned_count),
                )
                added += 1
        return added

    def breaches_for_identity(self, value: str) -> list[BreachRecord]:
        out: list[BreachRecord] = []
        target = value.strip().lower()
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM breaches WHERE identity_value=?", (target,)
            ).fetchall()
        for row in rows:
            out.append(self._row_to_breach(row))
        return out

    def all_breaches(self) -> list[BreachRecord]:
        out: list[BreachRecord] = []
        with self._conn() as c:
            rows = c.execute("SELECT * FROM breaches ORDER BY added_at DESC").fetchall()
        for row in rows:
            out.append(self._row_to_breach(row))
        return out

    @staticmethod
    def _row_to_breach(row) -> BreachRecord:
        from breach_sentinel.models import BreachType
        return BreachRecord(
            bid=row["bid"], source_id=row["source_id"],
            identity_value=row["identity_value"],
            breach_type=BreachType(row["breach_type"]),
            breach_name=row["breach_name"],
            breach_date=_dt_parse(row["breach_date"]),
            added_at=_dt_parse(row["added_at"]),
            description=row["description"] or "",
            password_pwned_count=row["password_pwned_count"],
        )

    # --- alerts ---
    def add_alerts(self, alerts: Iterable[Alert]) -> int:
        added = 0
        with self._conn() as c:
            for a in alerts:
                cur = c.execute("SELECT 1 FROM alerts WHERE aid=?", (a.aid,)).fetchone()
                if cur:
                    continue
                c.execute(
                    """INSERT INTO alerts (aid, iid, severity, title, body, created_at)
                       VALUES (?,?,?,?,?,?)""",
                    (a.aid, a.iid, a.severity.value, a.title, a.body, _dt_iso(a.created_at)),
                )
                added += 1
        return added

    def recent_alerts(self, limit: int = 50) -> list[Alert]:
        out: list[Alert] = []
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        for row in rows:
            out.append(self._row_to_alert(row))
        return out

    @staticmethod
    def _row_to_alert(row) -> Alert:
        from breach_sentinel.models import Severity
        return Alert(
            aid=row["aid"], iid=row["iid"], severity=Severity(row["severity"]),
            title=row["title"], body=row["body"], created_at=_dt_parse(row["created_at"]),
        )

    # --- scans ---
    def record_scan(self, result: ScanResult) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT INTO scans (iid, score, severity, record_count, scanned_at)
                   VALUES (?,?,?,?,?)""",
                (result.iid, result.score.score, result.score.severity.value,
                 result.score.record_count, _dt_iso(result.scanned_at)),
            )
