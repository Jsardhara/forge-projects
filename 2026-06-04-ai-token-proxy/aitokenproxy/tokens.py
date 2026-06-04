"""Token counting utilities for AITokenProxy.

Uses tiktoken for OpenAI models, approximate counting for others.
Falls back to character-based estimation when tiktoken is unavailable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Average characters per token across common tokenizers
_CHARS_PER_TOKEN = 4


@dataclass
class TokenCount:
    """Result of a token counting operation."""
    input_tokens: int
    output_tokens: int | None = None
    compressed_tokens: int | None = None
    savings_pct: float | None = None


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens in text for a given model.

    Uses tiktoken if available, falls back to char-based estimation.
    """
    if not text:
        return 0
    try:
        import tiktoken
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        logger.debug("tiktoken not available, using char-based estimation")
        return max(1, len(text) // _CHARS_PER_TOKEN)


def count_message_tokens(messages: list[dict], model: str = "gpt-4") -> int:
    """Count tokens in a list of chat messages.

    Each message has ~4 tokens of overhead plus the content tokens.
    """
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            # Multi-modal content (text + images)
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    total += count_tokens(part.get("text", ""), model)
                # Image tokens are roughly fixed
                elif isinstance(part, dict) and part.get("type") == "image_url":
                    total += 85  # Approximate for low-res images
        else:
            total += count_tokens(str(content), model)
        total += 4  # Message overhead
    total += 2  # Priming tokens
    return total


def compute_savings(original_tokens: int, compressed_tokens: int) -> tuple[int, float]:
    """Compute absolute and percentage token savings.

    Returns: (tokens_saved, savings_percentage)
    """
    saved = max(0, original_tokens - compressed_tokens)
    pct = (saved / original_tokens * 100) if original_tokens > 0 else 0.0
    return saved, round(pct, 1)


# Model pricing: (input_cost_per_1M_tokens, output_cost_per_1M_tokens)
PRICING = {
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4": (30.00, 60.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "o1": (15.00, 60.00),
    "o1-mini": (1.10, 4.40),
    "o3-mini": (1.10, 4.40),
    # Anthropic
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-opus-4-20250514": (15.00, 75.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.25, 1.25),
    "claude-3-opus": (15.00, 75.00),
    "claude-3-haiku": (0.25, 1.25),
    # Google
    "gemini-2.5-pro": (1.25, 5.00),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int = 0) -> float:
    """Estimate the cost of an API call in USD."""
    pricing = PRICING.get(model)
    if not pricing:
        # Default to GPT-4o pricing
        pricing = PRICING["gpt-4o"]
    input_cost = (input_tokens / 1_000_000) * pricing[0]
    output_cost = (output_tokens / 1_000_000) * pricing[1]
    return round(input_cost + output_cost, 6)
