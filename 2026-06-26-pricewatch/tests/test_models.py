"""Tests for PriceWatch models."""

import pytest
from datetime import datetime, timezone

from pricewatch.models import (
    AlertSeverity,
    ChangeDirection,
    ModelPricing,
    PriceAlert,
    PriceDelta,
    PriceSnapshot,
    Provider,
    Tier,
    ModelRanking,
)


class TestModelPricing:
    """Tests for ModelPricing dataclass."""

    def test_blended_price(self):
        mp = ModelPricing(
            provider=Provider.OPENAI, model_id="gpt-4o", tier=Tier.MID,
            input_price_per_mtok=2.50, output_price_per_mtok=10.00,
            context_window=128000,
        )
        assert mp.blended_price == pytest.approx(6.25)

    def test_price_per_1k_context(self):
        mp = ModelPricing(
            provider=Provider.OPENAI, model_id="gpt-4o", tier=Tier.MID,
            input_price_per_mtok=2.50, output_price_per_mtok=10.00,
            context_window=128000,
        )
        expected = 6.25 / (128000 / 1000)
        assert mp.price_per_1k_context == pytest.approx(expected)

    def test_zero_context_window_fallback(self):
        mp = ModelPricing(
            provider=Provider.OPENAI, model_id="test", tier=Tier.FAST,
            input_price_per_mtok=1.0, output_price_per_mtok=2.0,
            context_window=0,
        )
        assert mp.price_per_1k_context == pytest.approx(1.5)

    def test_snapshot_time_defaults_to_utc_now(self):
        mp = ModelPricing(
            provider=Provider.OPENAI, model_id="test", tier=Tier.FAST,
            input_price_per_mtok=1.0, output_price_per_mtok=2.0,
            context_window=1000,
        )
        assert mp.snapshot_time.tzinfo is not None


class TestPriceDelta:
    """Tests for PriceDelta dataclass."""

    def test_max_pct_returns_largest_absolute(self):
        delta = PriceDelta(
            provider=Provider.OPENAI, model_id="gpt-4o",
            direction=ChangeDirection.PRICE_DROP,
            input_delta=-0.50, output_delta=-2.00,
            input_pct=-20.0, output_pct=-20.0,
            old_input=2.50, old_output=10.00,
            new_input=2.00, new_output=8.00,
        )
        assert delta.max_pct == pytest.approx(20.0)

    def test_max_pct_asymmetric(self):
        delta = PriceDelta(
            provider=Provider.OPENAI, model_id="gpt-4o",
            direction=ChangeDirection.PRICE_DROP,
            input_delta=-0.50, output_delta=-5.00,
            input_pct=-20.0, output_pct=-50.0,
            old_input=2.50, old_output=10.00,
            new_input=2.00, new_output=5.00,
        )
        assert delta.max_pct == pytest.approx(50.0)


class TestPriceSnapshot:
    """Tests for PriceSnapshot filtering."""

    def _make_snapshot(self):
        entries = [
            ModelPricing(
                provider=Provider.OPENAI, model_id="gpt-4o", tier=Tier.MID,
                input_price_per_mtok=2.50, output_price_per_mtok=10.00,
                context_window=128000,
            ),
            ModelPricing(
                provider=Provider.ANTHROPIC, model_id="claude-haiku-3.5", tier=Tier.FAST,
                input_price_per_mtok=0.80, output_price_per_mtok=4.00,
                context_window=200000,
            ),
            ModelPricing(
                provider=Provider.GOOGLE, model_id="gemini-2.5-flash", tier=Tier.FAST,
                input_price_per_mtok=0.15, output_price_per_mtok=0.60,
                context_window=1000000,
            ),
        ]
        return PriceSnapshot(entries=entries)

    def test_by_provider(self):
        snap = self._make_snapshot()
        openai = snap.by_provider(Provider.OPENAI)
        assert len(openai) == 1
        assert openai[0].model_id == "gpt-4o"

    def test_by_tier(self):
        snap = self._make_snapshot()
        fast = snap.by_tier(Tier.FAST)
        assert len(fast) == 2

    def test_by_model(self):
        snap = self._make_snapshot()
        gpt4o = snap.by_model("gpt-4o")
        assert len(gpt4o) == 1


class TestEnums:
    """Tests for enum values."""

    def test_provider_values(self):
        assert Provider.OPENAI.value == "openai"
        assert Provider.ANTHROPIC.value == "anthropic"
        assert Provider.GOOGLE.value == "google"
        assert Provider.MISTRAL.value == "mistral"

    def test_tier_values(self):
        assert Tier.FLAGSHIP.value == "flagship"
        assert Tier.MID.value == "mid"
        assert Tier.FAST.value == "fast"

    def test_change_direction_values(self):
        assert ChangeDirection.PRICE_DROP.value == "price_drop"
        assert ChangeDirection.PRICE_INCREASE.value == "price_increase"

    def test_alert_severity_ordering(self):
        assert AlertSeverity.CRITICAL.value == "critical"
        assert AlertSeverity.HIGH.value == "high"
        assert AlertSeverity.MEDIUM.value == "medium"
        assert AlertSeverity.LOW.value == "low"
        assert AlertSeverity.INFO.value == "info"
