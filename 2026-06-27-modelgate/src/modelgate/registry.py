"""Default model registry — curated list of AI models with tier classifications."""

from __future__ import annotations

from .models import Model, ModelTier

# Curated as of 2026-06-27 based on public provider information.
# Tier assignment follows the US government vetting framework announced June 26, 2026.

DEFAULT_MODELS: list[Model] = [
    # --- PUBLIC ---
    Model(
        name="gpt-4o-mini",
        provider="OpenAI",
        tier=ModelTier.PUBLIC,
        description="Lightweight GPT-4o variant for everyday tasks",
    ),
    Model(
        name="claude-haiku-3.5",
        provider="Anthropic",
        tier=ModelTier.PUBLIC,
        description="Fast Claude variant for low-risk tasks",
    ),
    Model(
        name="gemini-2.0-flash-lite",
        provider="Google",
        tier=ModelTier.PUBLIC,
        description="Budget Gemini variant with wide availability",
    ),
    Model(
        name="mistral-small",
        provider="Mistral",
        tier=ModelTier.PUBLIC,
        description="Small Mistral model for general use",
    ),
    # --- RESTRICTED ---
    Model(
        name="gpt-4o",
        provider="OpenAI",
        tier=ModelTier.RESTRICTED,
        description="Full GPT-4o with usage restrictions",
    ),
    Model(
        name="claude-sonnet-4",
        provider="Anthropic",
        tier=ModelTier.RESTRICTED,
        description="Balanced Claude model with use-case restrictions",
    ),
    Model(
        name="gemini-2.5-pro",
        provider="Google",
        tier=ModelTier.RESTRICTED,
        description="Advanced Gemini with usage policies",
    ),
    Model(
        name="mistral-large",
        provider="Mistral",
        tier=ModelTier.RESTRICTED,
        description="Large Mistral model with provider restrictions",
    ),
    # --- CLASSIFIED ---
    Model(
        name="gpt-5.6",
        provider="OpenAI",
        tier=ModelTier.CLASSIFIED,
        description="GPT-5.6 — requires government vetting (announced June 2026)",
    ),
    Model(
        name="mythos",
        provider="Anthropic",
        tier=ModelTier.CLASSIFIED,
        description="Anthropic Mythos — released to 100+ trusted US orgs after NSA breach",
    ),
    Model(
        name="gemini-ultra-2",
        provider="Google",
        tier=ModelTier.CLASSIFIED,
        description="Ultra-tier Gemini with restricted access",
    ),
    # --- GOVERNMENT_VETTED ---
    Model(
        name="gpt-5.6-classified",
        provider="OpenAI",
        tier=ModelTier.GOVERNMENT_VETTED,
        description="GPT-5.6 classified variant — explicit government clearance required",
    ),
    Model(
        name="mythos-gov",
        provider="Anthropic",
        tier=ModelTier.GOVERNMENT_VETTED,
        description="Mythos government variant — national security clearance required",
    ),
]
