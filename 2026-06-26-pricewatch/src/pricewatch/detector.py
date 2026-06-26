"""Change detector — compare snapshots to find price deltas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .models import (
    ChangeDirection,
    ModelPricing,
    PriceDelta,
    PriceSnapshot,
    Provider,
)


def detect_changes(
    current: PriceSnapshot,
    previous: PriceSnapshot,
) -> list[PriceDelta]:
    """Detect pricing changes between two snapshots.

    Returns a PriceDelta for every model that appears in both snapshots
    with a different price, plus a NEW_MODEL delta for models only in current.
    """
    deltas: list[PriceDelta] = []

    # Build lookup for previous snapshot
    prev_by_key: dict[tuple[str, str], ModelPricing] = {}
    for e in previous.entries:
        prev_by_key[(e.provider.value, e.model_id)] = e

    # Build lookup for current snapshot (to detect removed models)
    curr_keys: set[tuple[str, str]] = set()
    for e in current.entries:
        curr_keys.add((e.provider.value, e.model_id))

    now = datetime.now(timezone.utc)

    # Compare current vs previous
    for entry in current.entries:
        key = (entry.provider.value, entry.model_id)
        prev = prev_by_key.get(key)

        if prev is None:
            # New model
            deltas.append(
                PriceDelta(
                    provider=entry.provider,
                    model_id=entry.model_id,
                    direction=ChangeDirection.NEW_MODEL,
                    input_delta=entry.input_price_per_mtok,
                    output_delta=entry.output_price_per_mtok,
                    input_pct=100.0,
                    output_pct=100.0,
                    old_input=0.0,
                    old_output=0.0,
                    new_input=entry.input_price_per_mtok,
                    new_output=entry.output_price_per_mtok,
                    detected_at=now,
                )
            )
            continue

        i_diff = entry.input_price_per_mtok - prev.input_price_per_mtok
        o_diff = entry.output_price_per_mtok - prev.output_price_per_mtok

        # Skip if no change (within floating point tolerance)
        if abs(i_diff) < 1e-9 and abs(o_diff) < 1e-9:
            continue

        # Calculate percentages (handle zero old price)
        i_pct = (i_diff / prev.input_price_per_mtok * 100) if prev.input_price_per_mtok > 0 else (100.0 if i_diff > 0 else 0.0)
        o_pct = (o_diff / prev.output_price_per_mtok * 100) if prev.output_price_per_mtok > 0 else (100.0 if o_diff > 0 else 0.0)

        # Determine direction
        if i_diff < 0 or o_diff < 0:
            direction = ChangeDirection.PRICE_DROP
        else:
            direction = ChangeDirection.PRICE_INCREASE

        deltas.append(
            PriceDelta(
                provider=entry.provider,
                model_id=entry.model_id,
                direction=direction,
                input_delta=i_diff,
                output_delta=o_diff,
                input_pct=i_pct,
                output_pct=o_pct,
                old_input=prev.input_price_per_mtok,
                old_output=prev.output_price_per_mtok,
                new_input=entry.input_price_per_mtok,
                new_output=entry.output_price_per_mtok,
                detected_at=now,
            )
        )

    return deltas


def detect_price_wars(
    deltas: list[PriceDelta],
    min_providers: int = 2,
    drop_threshold_pct: float = 10.0,
) -> list[list[PriceDelta]]:
    """Identify price wars — when multiple providers drop prices for similar-tier models.

    A price war is defined as >=min_providers with PRICE_DROP of >=drop_threshold_pct
    within the same time window.
    """
    drops = [d for d in deltas if d.direction == ChangeDirection.PRICE_DROP and d.max_pct >= drop_threshold_pct]

    if len(drops) < min_providers:
        return []

    # Group by provider
    by_provider: dict[Provider, list[PriceDelta]] = {}
    for d in drops:
        by_provider.setdefault(d.provider, []).append(d)

    # If at least min_providers distinct providers had drops, it's a price war
    if len(by_provider) >= min_providers:
        return [drops]

    return []
