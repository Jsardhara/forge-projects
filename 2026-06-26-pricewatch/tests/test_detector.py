"""Tests for PriceWatch change detector."""

import pytest
from datetime import datetime, timezone, timedelta

from pricewatch.models import (
    ChangeDirection,
    ModelPricing,
    PriceDelta,
    PriceSnapshot,
    Provider,
    Tier,
)
from pricewatch.detector import detect_changes, detect_price_wars


def _make_entry(
    provider: Provider,
    model_id: str,
    input_price: float,
    output_price: float,
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


class TestDetectChanges:
    """Tests for detect_changes function."""

    def test_no_changes(self):
        """No changes when snapshots are identical."""
        ts1 = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 6, 26, 12, 0, 0, tzinfo=timezone.utc)

        prev = PriceSnapshot(
            timestamp=ts1,
            entries=[_make_entry(Provider.OPENAI, "gpt-4o", 2.50, 10.00, ts1)],
        )
        curr = PriceSnapshot(
            timestamp=ts2,
            entries=[_make_entry(Provider.OPENAI, "gpt-4o", 2.50, 10.00, ts2)],
        )

        deltas = detect_changes(curr, prev)
        assert len(deltas) == 0

    def test_price_drop_detected(self):
        """Detect a price drop."""
        ts1 = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 6, 26, 12, 0, 0, tzinfo=timezone.utc)

        prev = PriceSnapshot(
            timestamp=ts1,
            entries=[_make_entry(Provider.OPENAI, "gpt-4o", 2.50, 10.00, ts1)],
        )
        curr = PriceSnapshot(
            timestamp=ts2,
            entries=[_make_entry(Provider.OPENAI, "gpt-4o", 2.00, 8.00, ts2)],
        )

        deltas = detect_changes(curr, prev)
        assert len(deltas) == 1
        assert deltas[0].direction == ChangeDirection.PRICE_DROP
        assert deltas[0].input_pct == pytest.approx(-20.0)
        assert deltas[0].output_pct == pytest.approx(-20.0)
        assert deltas[0].old_input == pytest.approx(2.50)
        assert deltas[0].new_input == pytest.approx(2.00)

    def test_price_increase_detected(self):
        """Detect a price increase."""
        ts1 = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 6, 26, 12, 0, 0, tzinfo=timezone.utc)

        prev = PriceSnapshot(
            timestamp=ts1,
            entries=[_make_entry(Provider.ANTHROPIC, "claude-sonnet-4", 3.00, 15.00, ts1)],
        )
        curr = PriceSnapshot(
            timestamp=ts2,
            entries=[_make_entry(Provider.ANTHROPIC, "claude-sonnet-4", 4.00, 20.00, ts2)],
        )

        deltas = detect_changes(curr, prev)
        assert len(deltas) == 1
        assert deltas[0].direction == ChangeDirection.PRICE_INCREASE
        assert deltas[0].input_pct == pytest.approx(33.333, rel=1e-3)

    def test_new_model_detected(self):
        """Detect a new model in the current snapshot."""
        ts1 = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 6, 26, 12, 0, 0, tzinfo=timezone.utc)

        prev = PriceSnapshot(
            timestamp=ts1,
            entries=[_make_entry(Provider.OPENAI, "gpt-4o", 2.50, 10.00, ts1)],
        )
        curr = PriceSnapshot(
            timestamp=ts2,
            entries=[
                _make_entry(Provider.OPENAI, "gpt-4o", 2.50, 10.00, ts2),
                _make_entry(Provider.OPENAI, "gpt-5", 5.00, 20.00, ts2),
            ],
        )

        deltas = detect_changes(curr, prev)
        assert len(deltas) == 1
        assert deltas[0].direction == ChangeDirection.NEW_MODEL
        assert deltas[0].model_id == "gpt-5"

    def test_mixed_changes(self):
        """One drops, one increases, one unchanged, one new."""
        ts1 = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 6, 26, 12, 0, 0, tzinfo=timezone.utc)

        prev = PriceSnapshot(
            timestamp=ts1,
            entries=[
                _make_entry(Provider.OPENAI, "gpt-4o", 2.50, 10.00, ts1),
                _make_entry(Provider.ANTHROPIC, "claude-sonnet-4", 3.00, 15.00, ts1),
                _make_entry(Provider.GOOGLE, "gemini-2.5-flash", 0.15, 0.60, ts1),
            ],
        )
        curr = PriceSnapshot(
            timestamp=ts2,
            entries=[
                _make_entry(Provider.OPENAI, "gpt-4o", 2.00, 8.00, ts2),  # drop
                _make_entry(Provider.ANTHROPIC, "claude-sonnet-4", 3.50, 17.50, ts2),  # increase
                _make_entry(Provider.GOOGLE, "gemini-2.5-flash", 0.15, 0.60, ts2),  # unchanged
                _make_entry(Provider.MISTRAL, "mistral-new", 1.00, 3.00, ts2),  # new
            ],
        )

        deltas = detect_changes(curr, prev)
        assert len(deltas) == 3
        directions = {d.model_id: d.direction for d in deltas}
        assert directions["gpt-4o"] == ChangeDirection.PRICE_DROP
        assert directions["claude-sonnet-4"] == ChangeDirection.PRICE_INCREASE
        assert directions["mistral-new"] == ChangeDirection.NEW_MODEL


class TestDetectPriceWars:
    """Tests for detect_price_wars function."""

    def test_no_price_war_single_provider(self):
        """A single provider dropping prices is not a price war."""
        delta = PriceDelta(
            provider=Provider.OPENAI, model_id="gpt-4o",
            direction=ChangeDirection.PRICE_DROP,
            input_delta=-0.50, output_delta=-2.00,
            input_pct=-20.0, output_pct=-20.0,
            old_input=2.50, old_output=10.00,
            new_input=2.00, new_output=8.00,
        )
        wars = detect_price_wars([delta])
        assert len(wars) == 0

    def test_price_war_multi_provider(self):
        """Two providers dropping prices = price war."""
        deltas = [
            PriceDelta(
                provider=Provider.OPENAI, model_id="gpt-4o",
                direction=ChangeDirection.PRICE_DROP,
                input_delta=-0.50, output_delta=-2.00,
                input_pct=-20.0, output_pct=-20.0,
                old_input=2.50, old_output=10.00,
                new_input=2.00, new_output=8.00,
            ),
            PriceDelta(
                provider=Provider.ANTHROPIC, model_id="claude-sonnet-4",
                direction=ChangeDirection.PRICE_DROP,
                input_delta=-0.60, output_delta=-3.00,
                input_pct=-20.0, output_pct=-20.0,
                old_input=3.00, old_output=15.00,
                new_input=2.40, new_output=12.00,
            ),
        ]
        wars = detect_price_wars(deltas)
        assert len(wars) == 1
        assert len(wars[0]) == 2

    def test_small_drop_no_war(self):
        """Drops below threshold don't count as price war."""
        deltas = [
            PriceDelta(
                provider=Provider.OPENAI, model_id="gpt-4o",
                direction=ChangeDirection.PRICE_DROP,
                input_delta=-0.10, output_delta=-0.40,
                input_pct=-4.0, output_pct=-4.0,
                old_input=2.50, old_output=10.00,
                new_input=2.40, new_output=9.60,
            ),
            PriceDelta(
                provider=Provider.ANTHROPIC, model_id="claude-sonnet-4",
                direction=ChangeDirection.PRICE_DROP,
                input_delta=-0.15, output_delta=-0.75,
                input_pct=-5.0, output_pct=-5.0,
                old_input=3.00, old_output=15.00,
                new_input=2.85, new_output=14.25,
            ),
        ]
        wars = detect_price_wars(deltas, drop_threshold_pct=10.0)
        assert len(wars) == 0
