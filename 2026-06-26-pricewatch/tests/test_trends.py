"""Tests for PriceWatch trend analysis."""

import os
import tempfile
import pytest
from datetime import datetime, timezone, timedelta

from pricewatch.models import ModelPricing, PriceSnapshot, Provider, Tier
from pricewatch.store import PriceStore
from pricewatch.trends import compute_trends, TrendPoint, ModelTrend


def _make_entry(ts: datetime, input_price: float = 2.50, output_price: float = 10.00) -> ModelPricing:
    return ModelPricing(
        provider=Provider.OPENAI,
        model_id="gpt-4o",
        tier=Tier.MID,
        input_price_per_mtok=input_price,
        output_price_per_mtok=output_price,
        context_window=128000,
        snapshot_time=ts,
    )


@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    import gc
    gc.collect()
    try:
        os.unlink(path)
    except PermissionError:
        pass


class TestTrendPoint:
    """Tests for TrendPoint."""

    def test_blended_calculation(self):
        tp = TrendPoint(
            timestamp=datetime.now(timezone.utc),
            input_price=2.50,
            output_price=10.00,
        )
        assert tp.blended == pytest.approx(6.25)


class TestModelTrend:
    """Tests for ModelTrend direction detection."""

    def test_stable_trend(self):
        now = datetime.now(timezone.utc)
        points = [
            TrendPoint(now - timedelta(days=2), 2.50, 10.00),
            TrendPoint(now - timedelta(days=1), 2.55, 10.10),
            TrendPoint(now, 2.50, 10.00),
        ]
        trend = ModelTrend(Provider.OPENAI, "gpt-4o", points)
        assert trend.direction == "stable"

    def test_decreasing_trend(self):
        now = datetime.now(timezone.utc)
        points = [
            TrendPoint(now - timedelta(days=2), 2.50, 10.00),
            TrendPoint(now - timedelta(days=1), 2.00, 8.00),
            TrendPoint(now, 1.50, 6.00),
        ]
        trend = ModelTrend(Provider.OPENAI, "gpt-4o", points)
        assert trend.direction == "decreasing"

    def test_increasing_trend(self):
        now = datetime.now(timezone.utc)
        points = [
            TrendPoint(now - timedelta(days=2), 2.50, 10.00),
            TrendPoint(now - timedelta(days=1), 3.00, 12.00),
            TrendPoint(now, 3.50, 14.00),
        ]
        trend = ModelTrend(Provider.OPENAI, "gpt-4o", points)
        assert trend.direction == "increasing"

    def test_single_point_stable(self):
        now = datetime.now(timezone.utc)
        points = [TrendPoint(now, 2.50, 10.00)]
        trend = ModelTrend(Provider.OPENAI, "gpt-4o", points)
        assert trend.direction == "stable"
        assert trend.total_pct == 0.0


class TestComputeTrends:
    """Tests for compute_trends with store."""

    def test_compute_trend_with_store(self, tmp_db):
        store = PriceStore(tmp_db)
        now = datetime.now(timezone.utc)

        for i in range(5):
            ts = now - timedelta(days=(4 - i))
            price = 2.50 - (i * 0.10)  # decreasing
            snap = PriceSnapshot(
                timestamp=ts,
                entries=[_make_entry(ts, input_price=price, output_price=price * 4)],
            )
            store.save_snapshot(snap)

        trend = compute_trends(store, "gpt-4o", days=30)
        assert trend is not None
        assert len(trend.points) == 5
        assert trend.direction == "decreasing"
        store.close()

    def test_no_data_returns_none(self, tmp_db):
        store = PriceStore(tmp_db)
        trend = compute_trends(store, "nonexistent", days=30)
        assert trend is None
        store.close()
