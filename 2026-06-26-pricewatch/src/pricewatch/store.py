"""Price store — SQLite-backed persistence for price snapshots over time."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import ModelPricing, PriceSnapshot, Provider, Tier


_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    model_id TEXT NOT NULL,
    tier TEXT NOT NULL,
    input_price REAL NOT NULL,
    output_price REAL NOT NULL,
    context_window INTEGER NOT NULL,
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
);

CREATE INDEX IF NOT EXISTS idx_prices_snapshot ON prices(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_prices_model ON prices(model_id);
"""


class PriceStore:
    """SQLite-backed store for price snapshots."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            db_path = str(Path.home() / ".pricewatch" / "prices.db")
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    def save_snapshot(self, snapshot: PriceSnapshot) -> int:
        """Save a price snapshot. Returns the snapshot ID."""
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO snapshots (timestamp) VALUES (?)",
            (snapshot.timestamp.isoformat(),),
        )
        snap_id = cur.lastrowid

        for entry in snapshot.entries:
            cur.execute(
                """INSERT INTO prices
                   (snapshot_id, provider, model_id, tier, input_price, output_price, context_window)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    snap_id,
                    entry.provider.value,
                    entry.model_id,
                    entry.tier.value,
                    entry.input_price_per_mtok,
                    entry.output_price_per_mtok,
                    entry.context_window,
                ),
            )

        self._conn.commit()
        return snap_id

    def latest_snapshot(self) -> Optional[PriceSnapshot]:
        """Retrieve the most recent snapshot."""
        row = self._conn.execute(
            "SELECT id, timestamp FROM snapshots ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return self._load_snapshot(row["id"], row["timestamp"])

    def previous_snapshot(self) -> Optional[PriceSnapshot]:
        """Retrieve the second-most-recent snapshot (for comparison)."""
        row = self._conn.execute(
            "SELECT id, timestamp FROM snapshots ORDER BY timestamp DESC LIMIT 1 OFFSET 1"
        ).fetchone()
        if row is None:
            return None
        return self._load_snapshot(row["id"], row["timestamp"])

    def snapshots_since(self, since: datetime) -> list[PriceSnapshot]:
        """Get all snapshots since a given datetime."""
        rows = self._conn.execute(
            "SELECT id, timestamp FROM snapshots WHERE timestamp >= ? ORDER BY timestamp ASC",
            (since.isoformat(),),
        ).fetchall()
        return [self._load_snapshot(r["id"], r["timestamp"]) for r in rows]

    def _load_snapshot(self, snap_id: int, ts_str: str) -> PriceSnapshot:
        rows = self._conn.execute(
            "SELECT * FROM prices WHERE snapshot_id = ?", (snap_id,)
        ).fetchall()
        entries = []
        for r in rows:
            entries.append(
                ModelPricing(
                    provider=Provider(r["provider"]),
                    model_id=r["model_id"],
                    tier=Tier(r["tier"]),
                    input_price_per_mtok=r["input_price"],
                    output_price_per_mtok=r["output_price"],
                    context_window=r["context_window"],
                    snapshot_time=datetime.fromisoformat(ts_str),
                )
            )
        return PriceSnapshot(
            timestamp=datetime.fromisoformat(ts_str),
            entries=entries,
        )

    def close(self) -> None:
        self._conn.close()
