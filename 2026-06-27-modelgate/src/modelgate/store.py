"""SQLite-backed store for ModelGate — employees, grants, requests, audit log."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import (
    AccessGrant,
    AccessRequest,
    AccessRequestStatus,
    AccessStatus,
    AuditEntry,
    ComplianceReport,
    Employee,
    Model,
    ModelTier,
)

_DEFAULT_DB = Path.home() / ".modelgate" / "modelgate.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    email TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS models (
    name TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    tier TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS access_grants (
    vid TEXT PRIMARY KEY,
    employee_email TEXT NOT NULL,
    tier TEXT NOT NULL,
    justification TEXT NOT NULL,
    approver TEXT NOT NULL,
    granted_at TEXT NOT NULL,
    expires_at TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    FOREIGN KEY (employee_email) REFERENCES employees(email)
);

CREATE TABLE IF NOT EXISTS access_requests (
    vid TEXT PRIMARY KEY,
    employee_email TEXT NOT NULL,
    tier TEXT NOT NULL,
    justification TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    reviewed_by TEXT,
    reviewed_at TEXT,
    denial_reason TEXT,
    FOREIGN KEY (employee_email) REFERENCES employees(email)
);

CREATE TABLE IF NOT EXISTS audit_log (
    vid TEXT PRIMARY KEY,
    employee_email TEXT NOT NULL,
    model_name TEXT NOT NULL,
    purpose TEXT NOT NULL,
    accessed_at TEXT NOT NULL,
    tier_at_access TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class ModelGateStore:
    """SQLite-backed store for all ModelGate data."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            db_path = str(_DEFAULT_DB)
        self._db_path = db_path
        p = Path(db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    # ── Employees ──────────────────────────────────────────

    def add_employee(self, email: str, name: str, department: str) -> Employee:
        now = _now_iso()
        self._conn.execute(
            "INSERT OR REPLACE INTO employees (email, name, department, created_at) VALUES (?, ?, ?, ?)",
            (email, name, department, now),
        )
        self._conn.commit()
        return Employee(email=email, name=name, department=department, created_at=_parse_dt(now))

    def get_employee(self, email: str) -> Optional[Employee]:
        row = self._conn.execute(
            "SELECT * FROM employees WHERE email = ?", (email,)
        ).fetchone()
        if row is None:
            return None
        return Employee(
            email=row["email"],
            name=row["name"],
            department=row["department"],
            created_at=_parse_dt(row["created_at"]),
        )

    def list_employees(self) -> list[Employee]:
        rows = self._conn.execute("SELECT * FROM employees ORDER BY email").fetchall()
        return [
            Employee(
                email=r["email"],
                name=r["name"],
                department=r["department"],
                created_at=_parse_dt(r["created_at"]),
            )
            for r in rows
        ]

    # ── Models ─────────────────────────────────────────────

    def register_model(self, name: str, provider: str, tier: ModelTier, description: str = "") -> Model:
        tier_str = tier.value
        self._conn.execute(
            "INSERT OR REPLACE INTO models (name, provider, tier, description) VALUES (?, ?, ?, ?)",
            (name, provider, tier_str, description),
        )
        self._conn.commit()
        return Model(name=name, provider=provider, tier=tier, description=description)

    def get_model(self, name: str) -> Optional[Model]:
        row = self._conn.execute(
            "SELECT * FROM models WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return None
        return Model(
            name=row["name"],
            provider=row["provider"],
            tier=ModelTier(row["tier"]),
            description=row["description"],
        )

    def list_models(self, tier: Optional[ModelTier] = None) -> list[Model]:
        if tier is not None:
            rows = self._conn.execute(
                "SELECT * FROM models WHERE tier = ? ORDER BY name", (tier.value,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM models ORDER BY tier, name").fetchall()
        return [
            Model(
                name=r["name"],
                provider=r["provider"],
                tier=ModelTier(r["tier"]),
                description=r["description"],
            )
            for r in rows
        ]

    # ── Access Grants ──────────────────────────────────────

    def grant_access(
        self,
        employee_email: str,
        tier: ModelTier,
        justification: str,
        approver: str,
        expires_at: Optional[datetime] = None,
    ) -> AccessGrant:
        vid = str(uuid.uuid4())[:8]
        now = _now_iso()
        expires_str = expires_at.isoformat() if expires_at else None
        self._conn.execute(
            "INSERT INTO access_grants (vid, employee_email, tier, justification, approver, granted_at, expires_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (vid, employee_email, tier.value, justification, approver, now, expires_str, AccessStatus.ACTIVE.value),
        )
        self._conn.commit()
        return AccessGrant(
            vid=vid,
            employee_email=employee_email,
            tier=tier,
            justification=justification,
            approver=approver,
            granted_at=_parse_dt(now),
            expires_at=expires_at,
            status=AccessStatus.ACTIVE,
        )

    def revoke_access(self, vid: str) -> Optional[AccessGrant]:
        now = _now_iso()
        self._conn.execute(
            "UPDATE access_grants SET status = ? WHERE vid = ?",
            (AccessStatus.REVOKED.value, vid),
        )
        self._conn.commit()
        return self.get_grant(vid)

    def get_grant(self, vid: str) -> Optional[AccessGrant]:
        row = self._conn.execute(
            "SELECT * FROM access_grants WHERE vid = ?", (vid,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_grant(row)

    def list_grants(
        self,
        employee_email: Optional[str] = None,
        tier: Optional[ModelTier] = None,
        status: Optional[AccessStatus] = None,
    ) -> list[AccessGrant]:
        query = "SELECT * FROM access_grants WHERE 1=1"
        params: list = []
        if employee_email:
            query += " AND employee_email = ?"
            params.append(employee_email)
        if tier:
            query += " AND tier = ?"
            params.append(tier.value)
        if status:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY granted_at DESC"
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_grant(r) for r in rows]

    def _row_to_grant(self, row: sqlite3.Row) -> AccessGrant:
        expires = row["expires_at"]
        return AccessGrant(
            vid=row["vid"],
            employee_email=row["employee_email"],
            tier=ModelTier(row["tier"]),
            justification=row["justification"],
            approver=row["approver"],
            granted_at=_parse_dt(row["granted_at"]),
            expires_at=_parse_dt(expires) if expires else None,
            status=AccessStatus(row["status"]),
        )

    # ── Access Requests ───────────────────────────────────

    def create_request(
        self,
        employee_email: str,
        tier: ModelTier,
        justification: str,
    ) -> AccessRequest:
        vid = str(uuid.uuid4())[:8]
        now = _now_iso()
        self._conn.execute(
            "INSERT INTO access_requests (vid, employee_email, tier, justification, requested_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (vid, employee_email, tier.value, justification, now, AccessRequestStatus.OPEN.value),
        )
        self._conn.commit()
        return AccessRequest(
            vid=vid,
            employee_email=employee_email,
            tier=tier,
            justification=justification,
            requested_at=_parse_dt(now),
            status=AccessRequestStatus.OPEN,
        )

    def approve_request(self, vid: str, approver: str) -> Optional[AccessRequest]:
        now = _now_iso()
        self._conn.execute(
            "UPDATE access_requests SET status = ?, reviewed_by = ?, reviewed_at = ? WHERE vid = ?",
            (AccessRequestStatus.APPROVED.value, approver, now, vid),
        )
        self._conn.commit()
        return self.get_request(vid)

    def deny_request(self, vid: str, approver: str, reason: str = "") -> Optional[AccessRequest]:
        now = _now_iso()
        self._conn.execute(
            "UPDATE access_requests SET status = ?, reviewed_by = ?, reviewed_at = ?, denial_reason = ? WHERE vid = ?",
            (AccessRequestStatus.DENIED.value, approver, now, reason, vid),
        )
        self._conn.commit()
        return self.get_request(vid)

    def get_request(self, vid: str) -> Optional[AccessRequest]:
        row = self._conn.execute(
            "SELECT * FROM access_requests WHERE vid = ?", (vid,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_request(row)

    def list_requests(
        self,
        status: Optional[AccessRequestStatus] = None,
    ) -> list[AccessRequest]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM access_requests WHERE status = ? ORDER BY requested_at DESC",
                (status.value,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM access_requests ORDER BY requested_at DESC"
            ).fetchall()
        return [self._row_to_request(r) for r in rows]

    def _row_to_request(self, row: sqlite3.Row) -> AccessRequest:
        reviewed_at = row["reviewed_at"]
        return AccessRequest(
            vid=row["vid"],
            employee_email=row["employee_email"],
            tier=ModelTier(row["tier"]),
            justification=row["justification"],
            requested_at=_parse_dt(row["requested_at"]),
            status=AccessRequestStatus(row["status"]),
            reviewed_by=row["reviewed_by"],
            reviewed_at=_parse_dt(reviewed_at) if reviewed_at else None,
            denial_reason=row["denial_reason"],
        )

    # ── Audit Log ──────────────────────────────────────────

    def log_access(
        self,
        employee_email: str,
        model_name: str,
        purpose: str,
        tier_at_access: ModelTier,
    ) -> AuditEntry:
        vid = str(uuid.uuid4())[:8]
        now = _now_iso()
        self._conn.execute(
            "INSERT INTO audit_log (vid, employee_email, model_name, purpose, accessed_at, tier_at_access) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (vid, employee_email, model_name, purpose, now, tier_at_access.value),
        )
        self._conn.commit()
        return AuditEntry(
            vid=vid,
            employee_email=employee_email,
            model_name=model_name,
            purpose=purpose,
            accessed_at=_parse_dt(now),
            tier_at_access=tier_at_access,
        )

    def list_audit(
        self,
        employee_email: Optional[str] = None,
        model_name: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        tier: Optional[ModelTier] = None,
    ) -> list[AuditEntry]:
        query = "SELECT * FROM audit_log WHERE 1=1"
        params: list = []
        if employee_email:
            query += " AND employee_email = ?"
            params.append(employee_email)
        if model_name:
            query += " AND model_name = ?"
            params.append(model_name)
        if since:
            query += " AND accessed_at >= ?"
            params.append(since.isoformat())
        if until:
            query += " AND accessed_at <= ?"
            params.append(until.isoformat())
        if tier:
            query += " AND tier_at_access = ?"
            params.append(tier.value)
        query += " ORDER BY accessed_at DESC"
        rows = self._conn.execute(query, params).fetchall()
        return [
            AuditEntry(
                vid=r["vid"],
                employee_email=r["employee_email"],
                model_name=r["model_name"],
                purpose=r["purpose"],
                accessed_at=_parse_dt(r["accessed_at"]),
                tier_at_access=ModelTier(r["tier_at_access"]),
            )
            for r in rows
        ]

    # ── Access Check ────────────────────────────────────────

    def check_access(self, employee_email: str, tier: ModelTier) -> bool:
        """Check if an employee has active access to a given tier."""
        now = datetime.now(timezone.utc).isoformat()
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM access_grants "
            "WHERE employee_email = ? AND tier = ? AND status = ?",
            (employee_email, tier.value, AccessStatus.ACTIVE.value),
        ).fetchone()
        return row["cnt"] > 0

    # ── Compliance Reports ──────────────────────────────────

    def generate_report(self, since: datetime, until: datetime) -> ComplianceReport:
        since_iso = since.isoformat()
        until_iso = until.isoformat()

        audit_rows = self._conn.execute(
            "SELECT * FROM audit_log WHERE accessed_at >= ? AND accessed_at <= ?",
            (since_iso, until_iso),
        ).fetchall()

        classified_count = sum(1 for r in audit_rows if r["tier_at_access"] in (ModelTier.CLASSIFIED.value, ModelTier.GOVERNMENT_VETTED.value))
        gov_vetted_count = sum(1 for r in audit_rows if r["tier_at_access"] == ModelTier.GOVERNMENT_VETTED.value)
        unique_employees = len(set(r["employee_email"] for r in audit_rows))

        expired_grants = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM access_grants WHERE status = ?",
            (AccessStatus.EXPIRED.value,),
        ).fetchone()["cnt"]
        revoked_grants = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM access_grants WHERE status = ?",
            (AccessStatus.REVOKED.value,),
        ).fetchone()["cnt"]
        pending_requests = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM access_requests WHERE status = ?",
            (AccessRequestStatus.OPEN.value,),
        ).fetchone()["cnt"]

        return ComplianceReport(
            since=since,
            until=until,
            total_accesses=len(audit_rows),
            unique_employees=unique_employees,
            classified_accesses=classified_count,
            government_vetted_accesses=gov_vetted_count,
            expired_grants=expired_grants,
            revoked_grants=revoked_grants,
            pending_requests=pending_requests,
        )

    # ── Access Review ──────────────────────────────────────

    def review_expired_grants(self) -> list[AccessGrant]:
        """Find grants that have expired but are still marked active."""
        now = datetime.now(timezone.utc).isoformat()
        rows = self._conn.execute(
            "SELECT * FROM access_grants WHERE status = ? AND expires_at IS NOT NULL AND expires_at < ?",
            (AccessStatus.ACTIVE.value, now),
        ).fetchall()
        return [self._row_to_grant(r) for r in rows]

    def expire_stale_grants(self) -> int:
        """Mark expired grants as expired. Returns count of updated grants."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            "UPDATE access_grants SET status = ? WHERE status = ? AND expires_at IS NOT NULL AND expires_at < ?",
            (AccessStatus.EXPIRED.value, AccessStatus.ACTIVE.value, now),
        )
        self._conn.commit()
        return cursor.rowcount
