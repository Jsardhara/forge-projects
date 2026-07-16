"""Model pricing for tokenaudit.

ILLUSTRATIVE public list prices in USD per 1,000,000 tokens, approximate as of
2026-06. These are reference defaults only -- override at runtime with
``--prices prices.json`` and verify against the providers' pricing pages before
making any billing decisions. Prices change; do not treat this table as authoritative.
"""
from __future__ import annotations

import json
from typing import Dict, Tuple

# model id (lowercased substring match) -> (input $/MTok, output $/MTok)
DEFAULT_PRICING: Dict[str, Tuple[float, float]] = {
    "claude-opus-4": (15.0, 75.0),
    "claude-sonnet-4": (3.0, 15.0),
    "claude-3-5-sonnet": (3.0, 15.0),
    "claude-3-5-haiku": (0.8, 4.0),
    "claude-3-haiku": (0.25, 1.25),
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.6),
    "o3": (10.0, 40.0),
    "o4-mini": (1.1, 4.4),
    "gemini-2.5-pro": (1.25, 10.0),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.0-flash": (0.10, 0.40),
}

FALLBACK = ("default", (3.0, 15.0))


def load_prices(path: str) -> Dict[str, Tuple[float, float]]:
    """Load a pricing override file. Expected JSON: {model: [in, out]}."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    out: Dict[str, Tuple[float, float]] = {}
    for k, v in data.items():
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            out[k.lower()] = (float(v[0]), float(v[1]))
    return out


def _resolve(model: str | None, table: Dict[str, Tuple[float, float]]) -> Tuple[float, float]:
    if not model:
        return table.get(FALLBACK[0], FALLBACK[1])
    m = model.lower()
    # exact then substring match
    if m in table:
        return table[m]
    for key, price in table.items():
        if key != FALLBACK[0] and key in m:
            return price
    return table.get(FALLBACK[0], FALLBACK[1])


def cost_for(model: str | None, input_tokens: int, output_tokens: int,
             table: Dict[str, Tuple[float, float]] | None = None) -> float:
    """Return cost in USD for a single message's usage."""
    t = table if table is not None else DEFAULT_PRICING
    inp, out = _resolve(model, t)
    return input_tokens / 1_000_000 * inp + output_tokens / 1_000_000 * out
