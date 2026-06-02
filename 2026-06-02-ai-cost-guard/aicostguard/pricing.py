"""Pricing data for supported AI providers — USD per 1K tokens."""

# Updated: 2026-06-02
# Source: https://openai.com/pricing, https://anthropic.com/pricing, https://ai.google.dev/pricing

OPENAI_PRICES: dict[str, dict[str, float]] = {
    # model: {input_per_1k, output_per_1k}
    "gpt-4o": {"input": 0.0025, "output": 0.010},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.010, "output": 0.030},
    "gpt-4": {"input": 0.030, "output": 0.060},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "o1": {"input": 0.015, "output": 0.060},
    "o1-mini": {"input": 0.003, "output": 0.012},
    "o3-mini": {"input": 0.0011, "output": 0.0044},
}

ANTHROPIC_PRICES: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "claude-sonnet-4-20250514-1M": {"input": 0.006, "output": 0.030},
    "claude-opus-4-20250514": {"input": 0.015, "output": 0.075},
    "claude-haiku-4-20250514": {"input": 0.00025, "output": 0.00125},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.00025, "output": 0.00125},
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
}

GOOGLE_PRICES: dict[str, dict[str, float]] = {
    "gemini-2.5-pro": {"input": 0.00125, "output": 0.010},
    "gemini-2.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-2.0-flash": {"input": 0.00010, "output": 0.0004},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
}

ALL_PRICES: dict[str, dict[str, dict[str, float]]] = {
    "openai": OPENAI_PRICES,
    "anthropic": ANTHROPIC_PRICES,
    "google": GOOGLE_PRICES,
}


def get_price(provider: str, model: str) -> dict[str, float]:
    """Get pricing for a specific model."""
    provider_prices = ALL_PRICES.get(provider.lower(), {})
    # Fuzzy model name matching
    model_lower = model.lower()
    for key, price in provider_prices.items():
        if key in model_lower or model_lower in key:
            return price
    return {}


def estimate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost for a given number of tokens."""
    price = get_price(provider, model)
    if not price:
        return 0.0
    return (input_tokens / 1000) * price.get("input", 0) + (output_tokens / 1000) * price.get("output", 0)
