"""Tests for PriceWatch ranking engine."""

import pytest
from datetime import datetime, timezone

from pricewatch.models import ModelPricing, PriceSnapshot, Provider, Tier
from pricewatch.ranking import compare_models, rank_all_tiers, rank_by_tier


def _make_entry(
    provider: Provider,
    model_id: str,
    tier: Tier,
    input_price: float,
    output_price: float,
) -> ModelPricing:
    return ModelPricing(
        provider=provider,
        model_id=model_id,
        tier=tier,
        input_price_per_mtok=input_price,
        output_price_per_mtok=output_price,
        context_window=128000,
    )


def _make_snapshot() -> PriceSnapshot:
    entries = [
        _make_entry(Provider.OPENAI, "gpt-4o", Tier.MID, 2.50, 10.00),
        _make_entry(Provider.OPENAI, "gpt-4o-mini", Tier.FAST, 0.15, 0.60),
        _make_entry(Provider.ANTHROPIC, "claude-sonnet-4", Tier.MID, 3.00, 15.00),
        _make_entry(Provider.ANTHROPIC, "claude-haiku-3.5", Tier.FAST, 0.80, 4.00),
        _make_entry(Provider.GOOGLE, "gemini-2.5-pro", Tier.MID, 1.25, 10.00),
        _make_entry(Provider.GOOGLE, "gemini-2.5-flash", Tier.FAST, 0.15, 0.60),
        _make_entry(Provider.MISTRAL, "mistral-small", Tier.FAST, 0.20, 0.60),
    ]
    return PriceSnapshot(
        timestamp=datetime.now(timezone.utc),
        entries=entries,
    )


class TestRankByTier:
    """Tests for rank_by_tier function."""

    def test_mid_tier_ranking(self):
        snap = _make_snapshot()
        rankings = rank_by_tier(snap, Tier.MID)
        assert len(rankings) == 3
        # Gemini Pro is cheapest blended: (1.25+10)/2 = 5.625
        # GPT-4o: (2.50+10)/2 = 6.25
        # Claude Sonnet: (3.00+15)/2 = 9.0
        assert rankings[0].pricing.model_id == "gemini-2.5-pro"
        assert rankings[0].rank == 1
        assert rankings[1].pricing.model_id == "gpt-4o"
        assert rankings[1].rank == 2
        assert rankings[2].pricing.model_id == "claude-sonnet-4"
        assert rankings[2].rank == 3

    def test_fast_tier_ranking(self):
        snap = _make_snapshot()
        rankings = rank_by_tier(snap, Tier.FAST)
        assert len(rankings) == 4
        # All should be sorted by blended price
        for i in range(len(rankings) - 1):
            assert rankings[i].score <= rankings[i + 1].score
        # gpt-4o-mini and gemini-2.5-flash should be cheapest (both 0.375 blended)
        assert rankings[0].score <= 0.40

    def test_empty_tier(self):
        snap = _make_snapshot()
        rankings = rank_by_tier(snap, Tier.FLAGSHIP)
        assert len(rankings) == 0

    def test_rank_by_input_price(self):
        snap = _make_snapshot()
        rankings = rank_by_tier(snap, Tier.MID, by="input")
        # Gemini: 1.25, GPT-4o: 2.50, Claude: 3.00
        assert rankings[0].pricing.model_id == "gemini-2.5-pro"


class TestRankAllTiers:
    """Tests for rank_all_tiers function."""

    def test_all_tiers_populated(self):
        snap = _make_snapshot()
        all_rankings = rank_all_tiers(snap)
        assert Tier.MID in all_rankings
        assert Tier.FAST in all_rankings
        assert Tier.FLAGSHIP not in all_rankings  # no flagship entries

    def test_total_model_count(self):
        snap = _make_snapshot()
        all_rankings = rank_all_tiers(snap)
        total = sum(len(v) for v in all_rankings.values())
        assert total == 7


class TestCompareModels:
    """Tests for compare_models function."""

    def test_specific_models(self):
        snap = _make_snapshot()
        rankings = compare_models(snap, ["gpt-4o", "claude-sonnet-4", "gemini-2.5-pro"])
        assert len(rankings) == 3
        assert rankings[0].pricing.model_id == "gemini-2.5-pro"  # cheapest
        assert rankings[0].rank == 1

    def test_missing_model_ignored(self):
        snap = _make_snapshot()
        rankings = compare_models(snap, ["gpt-4o", "nonexistent"])
        assert len(rankings) == 1
        assert rankings[0].model_id if hasattr(rankings[0], 'model_id') else rankings[0].pricing.model_id == "gpt-4o"
