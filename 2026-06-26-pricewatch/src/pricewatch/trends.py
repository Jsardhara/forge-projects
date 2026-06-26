"""Trend analysis — compute price trends over time."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from .models import ModelPricing, PriceSnapshot, Provider
from .store import PriceStore


class TrendPoint:
    """A single data point in a price trend."""

    __slots__ = ("timestamp", "input_price", "output_price", "blended")

    def __init__(
        self,
        timestamp: datetime,
        input_price: float,
        output_price: float,
    ) -> None:
        self.timestamp = timestamp
        self.input_price = input_price
        self.output_price = output_price
        self.blended = (input_price + output_price) / 2


class ModelTrend:
    """Price trend analysis for a single model."""

    __slots__ = ("provider", "model_id", "points", "direction", "total_pct")

    def __init__(
        self,
        provider: Provider,
        model_id: str,
        points: list[TrendPoint],
    ) -> None:
        self.provider = provider
        self.model_id = model_id
        self.points = points

        if len(points) < 2:
            self.direction = "stable"
            self.total_pct = 0.0
        else:
            first = points[0].blended
            last = points[-1].blended
            if first > 0:
                self.total_pct = ((last - first) / first) * 100
            else:
                self.total_pct = 0.0
            if self.total_pct < -5.0:
                self.direction = "decreasing"
            elif self.total_pct > 5.0:
                self.direction = "increasing"
            else:
                self.direction = "stable"


def compute_trends(
    store: PriceStore,
    model_id: str,
    days: int = 30,
) -> Optional[ModelTrend]:
    """Compute price trends for a specific model over N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    snapshots = store.snapshots_since(since)

    if not snapshots:
        return None

    points: list[TrendPoint] = []
    for snap in snapshots:
        for entry in snap.entries:
            if entry.model_id == model_id:
                points.append(
                    TrendPoint(
                        timestamp=entry.snapshot_time,
                        input_price=entry.input_price_per_mtok,
                        output_price=entry.output_price_per_mtok,
                    )
                )

    if not points:
        return None

    # Determine provider from first match
    provider = next(
        (e.provider for snap in snapshots for e in snap.entries if e.model_id == model_id),
        Provider.OPENAI,
    )

    return ModelTrend(
        provider=provider,
        model_id=model_id,
        points=sorted(points, key=lambda p: p.timestamp),
    )
