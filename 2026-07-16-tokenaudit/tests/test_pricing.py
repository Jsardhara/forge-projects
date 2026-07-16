from tokenaudit.pricing import cost_for, DEFAULT_PRICING, load_prices
import json
import tempfile
import os


def test_cost_for_known_model():
    # claude-sonnet-4: $3 in / $15 out per MTok
    c = cost_for("claude-sonnet-4", 1_000_000, 1_000_000)
    assert abs(c - 18.0) < 1e-6


def test_cost_for_substring_match():
    c = cost_for("claude-sonnet-4-20250514", 1_000_000, 0)
    assert abs(c - 3.0) < 1e-6


def test_cost_for_fallback():
    c = cost_for("some-unknown-model", 1_000_000, 0)
    # default 3.0 in / 15.0 out
    assert abs(c - 3.0) < 1e-6


def test_cost_for_none_model():
    c = cost_for(None, 1_000_000, 0)
    assert abs(c - 3.0) < 1e-6


def test_load_prices_override():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"custom-model": [1.0, 2.0]}, f)
        path = f.name
    try:
        table = load_prices(path)
        assert table["custom-model"] == (1.0, 2.0)
        # override changes cost
        c = cost_for("custom-model", 1_000_000, 0, table)
        assert abs(c - 1.0) < 1e-6
    finally:
        os.unlink(path)
