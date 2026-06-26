"""Tests for PriceWatch price store."""

import os
import tempfile
import pytest
from datetime import datetime, timezone, timedelta

from pricewatch.models import ModelPricing, PriceSnapshot, Provider, Tier
from pricewatch.store import PriceStore


def _make_entry(
    provider: Provider = Provider.OPENAI,
    model_id: str = "gpt-4o",
    input_price: float = 2.50,
    output_price: float = 10.00,
    ts: datetime | None = None,
) -> ModelPricing:
    return ModelPricing(
        provider=provider,
        model_id=model_id,
        tier=Tier.MID,
        input_price_per_mtok=input_price,
        output_price_per_mtok=output_price,
        context_window=128000,
        snapshot_time=ts or datetime.now(timezone.utc),
    )


@pytest.fixture
def tmp_db():
    """Provide a temporary database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    import gc
    gc.collect()
    try:
        os.unlink(path)
    except PermissionError:
        pass


class TestPriceStore:
    """Tests for PriceStore SQLite persistence."""

    def test_save_and_retrieve_snapshot(self, tmp_db):
        store = PriceStore(tmp_db)
        ts = datetime(2026, 6, 26, 12, 0, 0, tzinfo=timezone.utc)
        snap = PriceSnapshot(
            timestamp=ts,
            entries=[
                _make_entry(Provider.OPENAI, "gpt-4o", 2.50, 10.00, ts),
                _make_entry(Provider.ANTHROPIC, "claude-sonnet-4", 3.00, 15.00, ts),
            ],
        )
        snap_id = store.save_snapshot(snap)
        assert snap_id > 0

        retrieved = store.latest_snapshot()
        assert retrieved is not None
        assert len(retrieved.entries) == 2
        assert retrieved.entries[0].model_id == "gpt-4o"
        store.close()

    def test_latest_and_previous(self, tmp_db):
        store = PriceStore(tmp_db)
        ts1 = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 6, 26, 12, 0, 0, tzinfo=timezone.utc)

        snap1 = PriceSnapshot(timestamp=ts1, entries=[_make_entry(Provider.OPENAI, "gpt-4o", 2.50, 10.00, ts1)])
        snap2 = PriceSnapshot(timestamp=ts2, entries=[_make_entry(Provider.OPENAI, "gpt-4o", 2.00, 8.00, ts2)])

        store.save_snapshot(snap1)
        store.save_snapshot(snap2)

        latest = store.latest_snapshot()
        previous = store.previous_snapshot()

        assert latest is not None
        assert previous is not None
        assert latest.entries[0].input_price_per_mtok == pytest.approx(2.00)
        assert previous.entries[0].input_price_per_mtok == pytest.approx(2.50)
        store.close()

    def test_snapshots_since(self, tmp_db):
        store = PriceStore(tmp_db)
        base = datetime(2026, 6, 20, 12, 0, 0, tzinfo=timezone.utc)

        for i in range(5):
            ts = base + timedelta(days=i)
            snap = PriceSnapshot(timestamp=ts, entries=[_make_entry(Provider.OPENAI, "gpt-4o", 2.50, 10.00, ts)])
            store.save_snapshot(snap)

        since = base + timedelta(days=2)
        snapshots = store.snapshots_since(since)
        assert len(snapshots) == 3
        store.close()

    def test_empty_db_latest_none(self, tmp_db):
        store = PriceStore(tmp_db)
        assert store.latest_snapshot() is None
        assert store.previous_snapshot() is None
        store.close()
