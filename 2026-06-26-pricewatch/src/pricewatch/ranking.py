"""Ranking engine — rank models by cost-efficiency within tiers."""

from __future__ import annotations

from .models import ModelPricing, ModelRanking, PriceSnapshot, Tier


def rank_by_tier(
    snapshot: PriceSnapshot,
    tier: Tier,
    by: str = "blended",
) -> list[ModelRanking]:
    """Rank models in a tier by cost-efficiency.

    Args:
        snapshot: Price snapshot to rank.
        tier: Which tier to rank.
        by: Scoring method — "blended" (average of input+output),
            "input" (input price only), "output" (output price only),
            "context_efficiency" (price per 1K context tokens).

    Returns:
        List of ModelRanking sorted by score ascending (cheapest first).
    """
    entries = snapshot.by_tier(tier)

    if by == "blended":
        scored = [(e, e.blended_price) for e in entries]
    elif by == "input":
        scored = [(e, e.input_price_per_mtok) for e in entries]
    elif by == "output":
        scored = [(e, e.output_price_per_mtok) for e in entries]
    elif by == "context_efficiency":
        scored = [(e, e.price_per_1k_context) for e in entries]
    else:
        scored = [(e, e.blended_price) for e in entries]

    # Sort by score ascending (cheapest first)
    scored.sort(key=lambda x: x[1])

    return [
        ModelRanking(
            rank=i + 1,
            pricing=entry,
            score=score,
            tier=tier,
        )
        for i, (entry, score) in enumerate(scored)
    ]


def rank_all_tiers(
    snapshot: PriceSnapshot,
    by: str = "blended",
) -> dict[Tier, list[ModelRanking]]:
    """Rank models in all tiers."""
    result: dict[Tier, list[ModelRanking]] = {}
    for tier in Tier:
        rankings = rank_by_tier(snapshot, tier, by)
        if rankings:
            result[tier] = rankings
    return result


def compare_models(
    snapshot: PriceSnapshot,
    model_ids: list[str],
) -> list[ModelRanking]:
    """Compare specific models by cost-efficiency.

    Returns a ranking across the specified models regardless of tier.
    """
    entries = [e for e in snapshot.entries if e.model_id in model_ids]
    scored = sorted(entries, key=lambda e: e.blended_price)
    return [
        ModelRanking(
            rank=i + 1,
            pricing=entry,
            score=entry.blended_price,
            tier=entry.tier,
        )
        for i, entry in enumerate(scored)
    ]
