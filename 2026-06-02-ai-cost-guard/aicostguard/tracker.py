"""Core usage tracking and storage — SQLite-backed."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from aicostguard.pricing import estimate_cost, get_price


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost REAL NOT NULL DEFAULT 0,
    api_key_hash TEXT,
    team_id TEXT DEFAULT 'default',
    tags TEXT DEFAULT '',
    extra_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL DEFAULT 'default',
    provider TEXT NOT NULL DEFAULT 'all',
    model TEXT NOT NULL DEFAULT 'all',
    period TEXT NOT NULL DEFAULT 'daily',
    limit_usd REAL NOT NULL DEFAULT 0,
    alert_at_pct REAL NOT NULL DEFAULT 80,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL DEFAULT 'default',
    alert_type TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',
    created_at TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_records(timestamp);
CREATE INDEX IF NOT EXISTS idx_usage_team ON usage_records(team_id);
CREATE INDEX IF NOT EXISTS idx_usage_provider ON usage_records(provider);
CREATE INDEX IF NOT EXISTS idx_budgets_team ON budgets(team_id);
"""


@dataclass
class UsageRecord:
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    team_id: str = "default"
    tags: str = ""
    timestamp: str = ""
    id: Optional[int] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.estimated_cost == 0.0 and (self.input_tokens > 0 or self.output_tokens > 0):
            self.estimated_cost = estimate_cost(self.provider, self.model, self.input_tokens, self.output_tokens)


@dataclass
class Budget:
    team_id: str = "default"
    provider: str = "all"
    model: str = "all"
    period: str = "daily"
    limit_usd: float = 0.0
    alert_at_pct: float = 80.0
    created_at: str = ""
    id: Optional[int] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class Alert:
    team_id: str = "default"
    alert_type: str = "budget_warning"
    message: str = ""
    severity: str = "info"
    created_at: str = ""
    acknowledged: bool = False
    id: Optional[int] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class UsageTracker:
    """SQLite-backed usage tracker for AI API spending."""

    def __init__(self, db_path: str = "aicostguard.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(DB_SCHEMA)

    def record_usage(self, record: UsageRecord) -> int:
        """Record a usage event. Returns the row id."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """INSERT INTO usage_records
                   (timestamp, provider, model, input_tokens, output_tokens,
                    estimated_cost, team_id, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.timestamp,
                    record.provider,
                    record.model,
                    record.input_tokens,
                    record.output_tokens,
                    record.estimated_cost,
                    record.team_id,
                    record.tags,
                ),
            )
            return cur.lastrowid

    def get_total_spend(
        self,
        team_id: str = "default",
        provider: str = "all",
        model: str = "all",
        period: str = "daily",
    ) -> float:
        """Get total spend for a team/provider/model/period."""
        now = datetime.now(timezone.utc)
        if period == "daily":
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif period == "weekly":
            cutoff = __import__("datetime").datetime(
                now.year, now.month, now.day, tzinfo=timezone.utc
            ).timestamp() - 7 * 86400
            cutoff = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
        elif period == "monthly":
            cutoff = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        else:
            cutoff = "1970-01-01T00:00:00+00:00"

        query = "SELECT COALESCE(SUM(estimated_cost), 0) FROM usage_records WHERE team_id = ? AND timestamp >= ?"
        params: list = [team_id, cutoff]

        if provider != "all":
            query += " AND provider = ?"
            params.append(provider)
        if model != "all":
            query += " AND model = ?"
            params.append(model)

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(query, params).fetchone()
            return float(row[0]) if row else 0.0

    def get_spend_by_model(self, team_id: str = "default", period: str = "daily") -> list[dict]:
        """Get spend broken down by model."""
        now = datetime.now(timezone.utc)
        if period == "daily":
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif period == "weekly":
            cutoff = __import__("datetime").datetime(
                now.year, now.month, now.day, tzinfo=timezone.utc
            ).timestamp() - 7 * 86400
            cutoff = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
        elif period == "monthly":
            cutoff = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        else:
            cutoff = "1970-01-01T00:00:00+00:00"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT provider, model,
                          SUM(estimated_cost) as total_cost,
                          SUM(input_tokens) as total_input,
                          SUM(output_tokens) as total_output,
                          COUNT(*) as call_count
                   FROM usage_records
                   WHERE team_id = ? AND timestamp >= ?
                   GROUP BY provider, model
                   ORDER BY total_cost DESC""",
                (team_id, cutoff),
            ).fetchall()
            return [dict(r) for r in rows]

    def set_budget(self, budget: Budget) -> int:
        """Set a budget. Returns the row id."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """INSERT INTO budgets
                   (team_id, provider, model, period, limit_usd, alert_at_pct, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    budget.team_id,
                    budget.provider,
                    budget.model,
                    budget.period,
                    budget.limit_usd,
                    budget.alert_at_pct,
                    budget.created_at,
                ),
            )
            return cur.lastrowid

    def get_budgets(self, team_id: str = "default") -> list[dict]:
        """Get all budgets for a team."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM budgets WHERE team_id = ? ORDER BY created_at DESC",
                (team_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def check_budgets(self, team_id: str = "default") -> list[Alert]:
        """Check all budgets and return alerts for exceeded thresholds."""
        alerts = []
        budgets = self.get_budgets(team_id)
        for b in budgets:
            spend = self.get_total_spend(
                team_id=team_id,
                provider=b["provider"],
                model=b["model"],
                period=b["period"],
            )
            limit = b["limit_usd"]
            if limit <= 0:
                continue
            pct = (spend / limit) * 100
            if pct >= 100:
                alerts.append(Alert(
                    team_id=team_id,
                    alert_type="budget_exceeded",
                    message=f"Budget EXCEEDED: ${spend:.2f} / ${limit:.2f} ({pct:.0f}%) for {b['provider']}/{b['model']} ({b['period']})",
                    severity="alert",
                ))
            elif pct >= b["alert_at_pct"]:
                alerts.append(Alert(
                    team_id=team_id,
                    alert_type="budget_warning",
                    message=f"Budget warning: ${spend:.2f} / ${limit:.2f} ({pct:.0f}%) for {b['provider']}/{b['model']} ({b['period']})",
                    severity="warning",
                ))

        # Persist alerts
        with sqlite3.connect(self.db_path) as conn:
            for a in alerts:
                conn.execute(
                    """INSERT INTO alerts (team_id, alert_type, message, severity, created_at, acknowledged)
                       VALUES (?, ?, ?, ?, ?, 0)""",
                    (a.team_id, a.alert_type, a.message, a.severity, a.created_at),
                )
        return alerts

    def get_alerts(self, team_id: str = "default", unacknowledged_only: bool = True) -> list[dict]:
        """Get alerts for a team."""
        query = "SELECT * FROM alerts WHERE team_id = ?"
        params: list = [team_id]
        if unacknowledged_only:
            query += " AND acknowledged = 0"
        query += " ORDER BY created_at DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def acknowledge_alert(self, alert_id: int) -> bool:
        """Acknowledge an alert."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
            return cur.rowcount > 0

    def get_waste_report(self, team_id: str = "default", period: str = "daily") -> list[dict]:
        """Detect potential waste: expensive models where cheaper ones could work."""
        spend_by_model = self.get_spend_by_model(team_id, period)
        waste_items = []

        # Pairs of expensive -> cheaper alternatives
        cheaper_alternatives = {
            ("openai", "gpt-4o"): [("openai", "gpt-4o-mini"), ("openai", "o3-mini")],
            ("openai", "gpt-4-turbo"): [("openai", "gpt-4o"), ("openai", "gpt-4o-mini")],
            ("openai", "gpt-4"): [("openai", "gpt-4o"), ("openai", "gpt-4-turbo")],
            ("openai", "o1"): [("openai", "o1-mini"), ("openai", "o3-mini")],
            ("anthropic", "claude-opus-4-20250514"): [("anthropic", "claude-sonnet-4-20250514"), ("anthropic", "claude-haiku-4-20250514")],
            ("anthropic", "claude-sonnet-4-20250514"): [("anthropic", "claude-haiku-4-20250514")],
            ("anthropic", "claude-3-opus-20240229"): [("anthropic", "claude-3-5-sonnet-20241022")],
            ("google", "gemini-2.5-pro"): [("google", "gemini-2.5-flash")],
            ("google", "gemini-1.5-pro"): [("google", "gemini-1.5-flash")],
        }

        model_lookup = {(r["provider"], r["model"]): r for r in spend_by_model}

        for (prov, model), alt_list in cheaper_alternatives.items():
            current = model_lookup.get((prov, model))
            if not current or current["total_cost"] <= 0:
                continue
            for alt_prov, alt_model in alt_list:
                alt_price = get_price(alt_prov, alt_model)
                if not alt_price:
                    continue
                # Estimate savings if using the cheaper model
                total_in = current["total_input"]
                total_out = current["total_output"]
                current_cost = current["total_cost"]
                alt_cost = estimate_cost(alt_prov, alt_model, total_in, total_out)
                savings = current_cost - alt_cost
                if savings > 0.01:
                    waste_items.append({
                        "current_provider": prov,
                        "current_model": model,
                        "current_cost": round(current_cost, 4),
                        "suggested_provider": alt_prov,
                        "suggested_model": alt_model,
                        "estimated_alt_cost": round(alt_cost, 4),
                        "estimated_savings": round(savings, 4),
                        "savings_pct": round((savings / current_cost) * 100, 1) if current_cost > 0 else 0,
                        "call_count": current["call_count"],
                    })

        waste_items.sort(key=lambda x: x["estimated_savings"], reverse=True)
        return waste_items
