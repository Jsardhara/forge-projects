"""SQLite-backed storage for agents, budgets, probes, and alerts."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any


def get_db(path: Path | None = None) -> sqlite3.Connection:
    """Get a SQLite connection, creating tables if needed."""
    p = path or Path("agentwatch.db")
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            agent_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            provider TEXT NOT NULL DEFAULT 'openai',
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS spend_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            tokens_in INTEGER NOT NULL DEFAULT 0,
            tokens_out INTEGER NOT NULL DEFAULT 0,
            cost_usd REAL NOT NULL DEFAULT 0.0,
            recorded_at REAL NOT NULL,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        );

        CREATE TABLE IF NOT EXISTS budgets (
            agent_id TEXT PRIMARY KEY,
            daily_limit_usd REAL NOT NULL DEFAULT 5.0,
            monthly_limit_usd REAL NOT NULL DEFAULT 100.0,
            alert_threshold_pct REAL NOT NULL DEFAULT 80.0,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        );

        CREATE TABLE IF NOT EXISTS guardrail_probes (
            probe_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt TEXT NOT NULL,
            expected_keywords TEXT NOT NULL DEFAULT '[]',
            interval_seconds INTEGER NOT NULL DEFAULT 3600,
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS guardrail_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            probe_id TEXT NOT NULL,
            response_text TEXT,
            keywords_found TEXT NOT NULL DEFAULT '[]',
            keywords_missing TEXT NOT NULL DEFAULT '[]',
            drift_score REAL NOT NULL DEFAULT 0.0,
            passed INTEGER NOT NULL DEFAULT 1,
            checked_at REAL NOT NULL,
            FOREIGN KEY (probe_id) REFERENCES guardrail_probes(probe_id)
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            agent_id TEXT,
            probe_id TEXT,
            message TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'warn',
            created_at REAL NOT NULL,
            acknowledged INTEGER NOT NULL DEFAULT 0
        );
    """)
    conn.commit()


def register_agent(conn: sqlite3.Connection, agent_id: str, name: str, provider: str = "openai") -> dict[str, Any]:
    now = time.time()
    conn.execute(
        "INSERT OR REPLACE INTO agents (agent_id, name, provider, created_at) VALUES (?, ?, ?, ?)",
        (agent_id, name, provider, now),
    )
    # Set default budget
    conn.execute(
        "INSERT OR IGNORE INTO budgets (agent_id, daily_limit_usd, monthly_limit_usd, alert_threshold_pct) VALUES (?, 5.0, 100.0, 80.0)",
        (agent_id,),
    )
    conn.commit()
    return {"agent_id": agent_id, "name": name, "provider": provider, "created_at": now}


def list_agents(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM agents ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_agent(conn: sqlite3.Connection, agent_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
    return dict(row) if row else None


def record_spend(conn: sqlite3.Connection, agent_id: str, tokens_in: int, tokens_out: int, cost_usd: float) -> dict[str, Any]:
    now = time.time()
    conn.execute(
        "INSERT INTO spend_records (agent_id, tokens_in, tokens_out, cost_usd, recorded_at) VALUES (?, ?, ?, ?, ?)",
        (agent_id, tokens_in, tokens_out, cost_usd, now),
    )
    conn.commit()
    return {"agent_id": agent_id, "tokens_in": tokens_in, "tokens_out": tokens_out, "cost_usd": cost_usd, "recorded_at": now}


def get_spend(conn: sqlite3.Connection, agent_id: str, since: float | None = None) -> list[dict[str, Any]]:
    if since:
        rows = conn.execute(
            "SELECT * FROM spend_records WHERE agent_id = ? AND recorded_at >= ? ORDER BY recorded_at DESC",
            (agent_id, since),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM spend_records WHERE agent_id = ? ORDER BY recorded_at DESC",
            (agent_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_total_spend(conn: sqlite3.Connection, agent_id: str, since: float | None = None) -> float:
    if since:
        row = conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0.0) as total FROM spend_records WHERE agent_id = ? AND recorded_at >= ?",
            (agent_id, since),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0.0) as total FROM spend_records WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
    return float(row["total"]) if row else 0.0


def set_budget(conn: sqlite3.Connection, agent_id: str, daily_limit_usd: float, monthly_limit_usd: float, alert_threshold_pct: float = 80.0) -> dict[str, Any]:
    conn.execute(
        "INSERT OR REPLACE INTO budgets (agent_id, daily_limit_usd, monthly_limit_usd, alert_threshold_pct) VALUES (?, ?, ?, ?)",
        (agent_id, daily_limit_usd, monthly_limit_usd, alert_threshold_pct),
    )
    conn.commit()
    return {"agent_id": agent_id, "daily_limit_usd": daily_limit_usd, "monthly_limit_usd": monthly_limit_usd, "alert_threshold_pct": alert_threshold_pct}


def get_budget(conn: sqlite3.Connection, agent_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM budgets WHERE agent_id = ?", (agent_id,)).fetchone()
    return dict(row) if row else None


def create_guardrail_probe(conn: sqlite3.Connection, probe_id: str, name: str, provider: str, model: str, prompt: str, expected_keywords: str = "[]", interval_seconds: int = 3600) -> dict[str, Any]:
    now = time.time()
    conn.execute(
        "INSERT OR REPLACE INTO guardrail_probes (probe_id, name, provider, model, prompt, expected_keywords, interval_seconds, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (probe_id, name, provider, model, prompt, expected_keywords, interval_seconds, now),
    )
    conn.commit()
    return {"probe_id": probe_id, "name": name, "provider": provider, "model": model, "prompt": prompt, "expected_keywords": expected_keywords, "interval_seconds": interval_seconds, "created_at": now}


def list_guardrail_probes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM guardrail_probes ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_guardrail_probe(conn: sqlite3.Connection, probe_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM guardrail_probes WHERE probe_id = ?", (probe_id,)).fetchone()
    return dict(row) if row else None


def record_guardrail_result(conn: sqlite3.Connection, probe_id: str, response_text: str, keywords_found: str, keywords_missing: str, drift_score: float, passed: bool) -> dict[str, Any]:
    now = time.time()
    conn.execute(
        "INSERT INTO guardrail_results (probe_id, response_text, keywords_found, keywords_missing, drift_score, passed, checked_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (probe_id, response_text, keywords_found, keywords_missing, drift_score, int(passed), now),
    )
    conn.commit()
    return {"probe_id": probe_id, "drift_score": drift_score, "passed": passed, "checked_at": now}


def get_guardrail_results(conn: sqlite3.Connection, probe_id: str, limit: int = 10) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM guardrail_results WHERE probe_id = ? ORDER BY checked_at DESC LIMIT ?",
        (probe_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def create_alert(conn: sqlite3.Connection, alert_type: str, message: str, severity: str = "warn", agent_id: str | None = None, probe_id: str | None = None) -> dict[str, Any]:
    now = time.time()
    conn.execute(
        "INSERT INTO alerts (alert_type, agent_id, probe_id, message, severity, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (alert_type, agent_id, probe_id, message, severity, now),
    )
    conn.commit()
    return {"alert_type": alert_type, "message": message, "severity": severity, "created_at": now}


def list_alerts(conn: sqlite3.Connection, unread_only: bool = False, limit: int = 50) -> list[dict[str, Any]]:
    if unread_only:
        rows = conn.execute(
            "SELECT * FROM alerts WHERE acknowledged = 0 ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def acknowledge_alert(conn: sqlite3.Connection, alert_id: int) -> bool:
    cur = conn.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
    conn.commit()
    return cur.rowcount > 0
