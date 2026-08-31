"""Built-in curated plan registry plus helpers to map provider->plans."""
from __future__ import annotations

from capalarm.models import Plan

# Curated plan caps. These are best-effort public consumer figures (tokens/mo,
# rate tiers). Treat as editable presets; bring your own config for precision.
DEFAULT_PLANS: list[Plan] = [
    Plan(
        id="anthropic-claude-max",
        provider="anthropic",
        name="Claude Max (Pro)",
        hard_cap=2_000_000,
        soft_cap=1_600_000,
        rate_limit=60_000,
    ),
    Plan(
        id="anthropic-claude-max-premium",
        provider="anthropic",
        name="Claude Max (Premium)",
        hard_cap=8_000_000,
        soft_cap=6_400_000,
        rate_limit=60_000,
    ),
    Plan(
        id="openai-chatgpt-plus",
        provider="openai",
        name="ChatGPT Plus",
        hard_cap=1_200_000,
        soft_cap=960_000,
        rate_limit=30_000,
    ),
    Plan(
        id="google-gemini-ultra",
        provider="google",
        name="Gemini Ultra",
        hard_cap=2_500_000,
        soft_cap=2_000_000,
        rate_limit=40_000,
    ),
]


def plans_for_provider(provider: str, plans: list[Plan] | None = None) -> list[Plan]:
    """Return all default plans that target a given provider slug."""
    source = plans if plans is not None else DEFAULT_PLANS
    return [p for p in source if p.provider == provider]


def prefer_plan(provider: str, plans: list[Plan] | None = None) -> Plan | None:
    """Pick the largest-cap default plan for a provider (most useful ceiling)."""
    matches = plans_for_provider(provider, plans)
    if not matches:
        return None
    return max(matches, key=lambda p: p.hard_cap)