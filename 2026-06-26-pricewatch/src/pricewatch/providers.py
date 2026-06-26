"""Known model pricing data — curated snapshot of current LLM API prices.

These are structured reference prices (USD per 1M tokens) as of 2026-06-26.
In production, these would be scraped from provider pricing pages.
This module provides the static baseline for testing and offline use.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .models import ModelPricing, Provider, Tier, PriceSnapshot


# --- OpenAI ---
OPENAI_MODELS: list[ModelPricing] = [
    ModelPricing(
        provider=Provider.OPENAI, model_id="gpt-4o", tier=Tier.MID,
        input_price_per_mtok=2.50, output_price_per_mtok=10.00,
        context_window=128000,
    ),
    ModelPricing(
        provider=Provider.OPENAI, model_id="gpt-4o-mini", tier=Tier.FAST,
        input_price_per_mtok=0.15, output_price_per_mtok=0.60,
        context_window=128000,
    ),
    ModelPricing(
        provider=Provider.OPENAI, model_id="o3", tier=Tier.REASONING,
        input_price_per_mtok=2.00, output_price_per_mtok=8.00,
        context_window=200000,
    ),
    ModelPricing(
        provider=Provider.OPENAI, model_id="o3-mini", tier=Tier.REASONING,
        input_price_per_mtok=1.10, output_price_per_mtok=4.40,
        context_window=200000,
    ),
    ModelPricing(
        provider=Provider.OPENAI, model_id="gpt-4.1", tier=Tier.FLAGSHIP,
        input_price_per_mtok=2.00, output_price_per_mtok=8.00,
        context_window=128000,
    ),
    ModelPricing(
        provider=Provider.OPENAI, model_id="gpt-4.1-mini", tier=Tier.MID,
        input_price_per_mtok=0.40, output_price_per_mtok=1.60,
        context_window=128000,
    ),
    ModelPricing(
        provider=Provider.OPENAI, model_id="gpt-4.1-nano", tier=Tier.FAST,
        input_price_per_mtok=0.10, output_price_per_mtok=0.40,
        context_window=128000,
    ),
    ModelPricing(
        provider=Provider.OPENAI, model_id="text-embedding-3-large", tier=Tier.EMBEDDING,
        input_price_per_mtok=0.13, output_price_per_mtok=0.0,
        context_window=8192,
    ),
]

# --- Anthropic ---
ANTHROPIC_MODELS: list[ModelPricing] = [
    ModelPricing(
        provider=Provider.ANTHROPIC, model_id="claude-opus-4", tier=Tier.FLAGSHIP,
        input_price_per_mtok=15.00, output_price_per_mtok=75.00,
        context_window=200000,
    ),
    ModelPricing(
        provider=Provider.ANTHROPIC, model_id="claude-sonnet-4", tier=Tier.MID,
        input_price_per_mtok=3.00, output_price_per_mtok=15.00,
        context_window=200000,
    ),
    ModelPricing(
        provider=Provider.ANTHROPIC, model_id="claude-haiku-3.5", tier=Tier.FAST,
        input_price_per_mtok=0.80, output_price_per_mtok=4.00,
        context_window=200000,
    ),
]

# --- Google ---
GOOGLE_MODELS: list[ModelPricing] = [
    ModelPricing(
        provider=Provider.GOOGLE, model_id="gemini-2.5-pro", tier=Tier.MID,
        input_price_per_mtok=1.25, output_price_per_mtok=10.00,
        context_window=1000000,
    ),
    ModelPricing(
        provider=Provider.GOOGLE, model_id="gemini-2.5-flash", tier=Tier.FAST,
        input_price_per_mtok=0.15, output_price_per_mtok=0.60,
        context_window=1000000,
    ),
    ModelPricing(
        provider=Provider.GOOGLE, model_id="gemini-2.0-flash-lite", tier=Tier.FAST,
        input_price_per_mtok=0.075, output_price_per_mtok=0.30,
        context_window=1000000,
    ),
]

# --- Mistral ---
MISTRAL_MODELS: list[ModelPricing] = [
    ModelPricing(
        provider=Provider.MISTRAL, model_id="mistral-large", tier=Tier.MID,
        input_price_per_mtok=2.00, output_price_per_mtok=6.00,
        context_window=128000,
    ),
    ModelPricing(
        provider=Provider.MISTRAL, model_id="mistral-medium", tier=Tier.MID,
        input_price_per_mtok=0.70, output_price_per_mtok=2.80,
        context_window=128000,
    ),
    ModelPricing(
        provider=Provider.MISTRAL, model_id="mistral-small", tier=Tier.FAST,
        input_price_per_mtok=0.20, output_price_per_mtok=0.60,
        context_window=128000,
    ),
]


def current_snapshot() -> PriceSnapshot:
    """Return a snapshot with all known model pricing."""
    all_models = OPENAI_MODELS + ANTHROPIC_MODELS + GOOGLE_MODELS + MISTRAL_MODELS
    return PriceSnapshot(
        timestamp=datetime.now(timezone.utc),
        entries=all_models,
    )
