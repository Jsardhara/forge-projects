"""Tests for AI Cost Guard."""

import os
import tempfile
from unittest.mock import MagicMock

import pytest

from aicostguard.pricing import ALL_PRICES, estimate_cost, get_price
from aicostguard.tracker import Budget, UsageRecord, UsageTracker
from aicostguard.middleware import CostGuardMiddleware, OpenAIInterceptor, AnthropicInterceptor


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # On Windows, SQLite connections must be closed before unlink
    import gc
    gc.collect()
    try:
        os.unlink(path)
    except PermissionError:
        pass  # Windows file locking — cleaned up by OS eventually


@pytest.fixture
def tracker(tmp_db):
    """Create a tracker with a temp db."""
    return UsageTracker(db_path=tmp_db)


# ── Pricing Tests ───────────────────────────────────────────────────────────

class TestPricing:
    def test_get_price_openai_gpt4o(self):
        price = get_price("openai", "gpt-4o")
        assert price["input"] == 0.0025
        assert price["output"] == 0.010

    def test_get_price_anthropic_sonnet(self):
        price = get_price("anthropic", "claude-sonnet-4-20250514")
        assert price["input"] == 0.003
        assert price["output"] == 0.015

    def test_get_price_google_flash(self):
        price = get_price("google", "gemini-2.5-flash")
        assert price["input"] == 0.000075
        assert price["output"] == 0.0003

    def test_get_price_unknown_model(self):
        price = get_price("openai", "totally-fake-model")
        assert price == {}

    def test_estimate_cost_basic(self):
        cost = estimate_cost("openai", "gpt-4o", 1000, 500)
        expected = (1000 / 1000) * 0.0025 + (500 / 1000) * 0.010
        assert abs(cost - expected) < 1e-9

    def test_estimate_cost_zero_tokens(self):
        cost = estimate_cost("openai", "gpt-4o", 0, 0)
        assert cost == 0.0

    def test_estimate_cost_unknown_model(self):
        cost = estimate_cost("openai", "fake", 1000, 1000)
        assert cost == 0.0

    def test_estimate_cost_large_volume(self):
        cost = estimate_cost("openai", "gpt-4o", 1_000_000, 500_000)
        expected = (1_000_000 / 1000) * 0.0025 + (500_000 / 1000) * 0.010
        assert abs(cost - expected) < 1e-6

    def test_all_prices_have_three_providers(self):
        assert "openai" in ALL_PRICES
        assert "anthropic" in ALL_PRICES
        assert "google" in ALL_PRICES

    def test_prices_are_reasonable(self):
        """No negative or absurdly high prices."""
        for provider, models in ALL_PRICES.items():
            for model, prices in models.items():
                assert prices["input"] >= 0, f"{provider}/{model} negative input price"
                assert prices["output"] >= 0, f"{provider}/{model} negative output price"
                assert prices["input"] < 1.0, f"{provider}/{model} absurd input price"
                assert prices["output"] < 1.0, f"{provider}/{model} absurd output price"


# ── UsageRecord Tests ──────────────────────────────────────────────────────

class TestUsageRecord:
    def test_auto_cost_calculation(self):
        record = UsageRecord(
            provider="openai",
            model="gpt-4o",
            input_tokens=2000,
            output_tokens=1000,
        )
        expected = estimate_cost("openai", "gpt-4o", 2000, 1000)
        assert abs(record.estimated_cost - expected) < 1e-9

    def test_zero_tokens(self):
        record = UsageRecord(provider="openai", model="gpt-4o")
        assert record.estimated_cost == 0.0

    def test_auto_timestamp(self):
        record = UsageRecord(provider="openai", model="gpt-4o")
        assert record.timestamp != ""

    def test_custom_timestamp(self):
        record = UsageRecord(provider="openai", model="gpt-4o", timestamp="2026-01-01T00:00:00+00:00")
        assert record.timestamp == "2026-01-01T00:00:00+00:00"

    def test_team_id_default(self):
        record = UsageRecord(provider="openai", model="gpt-4o")
        assert record.team_id == "default"

    def test_custom_team_id(self):
        record = UsageRecord(provider="openai", model="gpt-4o", team_id="acme-corp")
        assert record.team_id == "acme-corp"


# ── Tracker Tests ───────────────────────────────────────────────────────────

class TestUsageTracker:
    def test_record_and_retrieve(self, tracker):
        record = UsageRecord(provider="openai", model="gpt-4o", input_tokens=1000, output_tokens=500)
        row_id = tracker.record_usage(record)
        assert row_id > 0

    def test_total_spend_empty(self, tracker):
        spend = tracker.get_total_spend()
        assert spend == 0.0

    def test_total_spend_after_records(self, tracker):
        tracker.record_usage(UsageRecord(provider="openai", model="gpt-4o", input_tokens=10000, output_tokens=5000))
        tracker.record_usage(UsageRecord(provider="anthropic", model="claude-sonnet-4-20250514", input_tokens=20000, output_tokens=10000))
        spend = tracker.get_total_spend(period="all")
        assert spend > 0

    def test_spend_by_model(self, tracker):
        tracker.record_usage(UsageRecord(provider="openai", model="gpt-4o", input_tokens=5000, output_tokens=2000))
        tracker.record_usage(UsageRecord(provider="openai", model="gpt-4o-mini", input_tokens=10000, output_tokens=5000))
        tracker.record_usage(UsageRecord(provider="anthropic", model="claude-sonnet-4-20250514", input_tokens=5000, output_tokens=2000))
        by_model = tracker.get_spend_by_model(period="all")
        assert len(by_model) == 3

    def test_team_isolation(self, tracker):
        tracker.record_usage(UsageRecord(provider="openai", model="gpt-4o", input_tokens=100000, output_tokens=50000, team_id="team-a"))
        tracker.record_usage(UsageRecord(provider="openai", model="gpt-4o", input_tokens=200000, output_tokens=100000, team_id="team-b"))

        spend_a = tracker.get_total_spend(team_id="team-a", period="all")
        spend_b = tracker.get_total_spend(team_id="team-b", period="all")
        assert spend_b > spend_a

    def test_filter_by_provider(self, tracker):
        tracker.record_usage(UsageRecord(provider="openai", model="gpt-4o", input_tokens=10000, output_tokens=5000))
        tracker.record_usage(UsageRecord(provider="anthropic", model="claude-sonnet-4-20250514", input_tokens=10000, output_tokens=5000))
        openai_spend = tracker.get_total_spend(provider="openai", period="all")
        anthropic_spend = tracker.get_total_spend(provider="anthropic", period="all")
        assert openai_spend > 0
        assert anthropic_spend > 0


# ── Budget Tests ────────────────────────────────────────────────────────────

class TestBudgets:
    def test_set_budget(self, tracker):
        budget = Budget(team_id="test", provider="openai", model="all", period="daily", limit_usd=50.0)
        row_id = tracker.set_budget(budget)
        assert row_id > 0

    def test_list_budgets(self, tracker):
        tracker.set_budget(Budget(team_id="test", limit_usd=50.0))
        tracker.set_budget(Budget(team_id="test", provider="anthropic", limit_usd=100.0))
        budgets = tracker.get_budgets(team_id="test")
        assert len(budgets) >= 2

    def test_budget_not_exceeded(self, tracker):
        tracker.set_budget(Budget(team_id="test", provider="openai", period="all", limit_usd=1000.0))
        tracker.record_usage(UsageRecord(provider="openai", model="gpt-4o", input_tokens=1000, output_tokens=500))
        alerts = tracker.check_budgets(team_id="test")
        assert len(alerts) == 0

    def test_budget_exceeded(self, tracker):
        # Set a very low budget that will be exceeded
        tracker.set_budget(Budget(team_id="test", period="daily", limit_usd=0.001))
        tracker.record_usage(UsageRecord(provider="openai", model="gpt-4o", input_tokens=10000, output_tokens=5000, team_id="test"))
        alerts = tracker.check_budgets(team_id="test")
        assert any(a.alert_type == "budget_exceeded" for a in alerts)

    def test_alert_persistence(self, tracker):
        tracker.set_budget(Budget(team_id="test", period="daily", limit_usd=0.001))
        tracker.record_usage(UsageRecord(provider="openai", model="gpt-4o", input_tokens=10000, output_tokens=5000, team_id="test"))
        tracker.check_budgets(team_id="test")
        alerts = tracker.get_alerts(team_id="test")
        assert len(alerts) > 0

    def test_acknowledge_alert(self, tracker):
        tracker.set_budget(Budget(team_id="test", period="daily", limit_usd=0.001))
        tracker.record_usage(UsageRecord(provider="openai", model="gpt-4o", input_tokens=10000, output_tokens=5000, team_id="test"))
        tracker.check_budgets(team_id="test")
        alerts = tracker.get_alerts(team_id="test", unacknowledged_only=True)
        if alerts:
            result = tracker.acknowledge_alert(alerts[0]["id"])
            assert result is True


# ── Waste Report Tests ─────────────────────────────────────────────────────

class TestWasteReport:
    def test_empty_waste_report(self, tracker):
        waste = tracker.get_waste_report(period="all")
        assert waste == []

    def test_gpt4o_to_gpt4o_mini_savings(self, tracker):
        # Use gpt-4o (expensive) — should suggest gpt-4o-mini (cheap)
        tracker.record_usage(UsageRecord(
            provider="openai", model="gpt-4o",
            input_tokens=100000, output_tokens=50000,
        ))
        waste = tracker.get_waste_report(period="all")
        assert len(waste) > 0
        first = waste[0]
        assert first["current_model"] == "gpt-4o"
        assert first["estimated_savings"] > 0

    def test_opus_to_haiku_savings(self, tracker):
        tracker.record_usage(UsageRecord(
            provider="anthropic", model="claude-opus-4-20250514",
            input_tokens=100000, output_tokens=50000,
        ))
        waste = tracker.get_waste_report(period="all")
        assert any(w["current_model"] == "claude-opus-4-20250514" for w in waste)

    def test_cheap_model_no_waste(self, tracker):
        # gpt-4o-mini is already the cheapest, no waste expected
        tracker.record_usage(UsageRecord(
            provider="openai", model="gpt-4o-mini",
            input_tokens=100000, output_tokens=50000,
        ))
        waste = tracker.get_waste_report(period="all")
        assert all(w["current_model"] != "gpt-4o-mini" for w in waste)


# ── Middleware Tests ────────────────────────────────────────────────────────

class TestMiddleware:
    def test_manual_track(self, tmp_db):
        tracker_obj = UsageTracker(db_path=tmp_db)
        mw = CostGuardMiddleware(tracker=tracker_obj, team_id="test")
        cost = mw.track("openai", "gpt-4o", 1000, 500)
        assert cost > 0
        spend = tracker_obj.get_total_spend(team_id="test", period="all")
        assert abs(spend - cost) < 1e-9

    def test_manual_track_unknown_model(self, tmp_db):
        tracker_obj = UsageTracker(db_path=tmp_db)
        mw = CostGuardMiddleware(tracker=tracker_obj)
        cost = mw.track("openai", "fake-model", 1000, 500)
        assert cost == 0.0

    def test_openai_interceptor(self, tmp_db):
        tracker_obj = UsageTracker(db_path=tmp_db)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.model = "gpt-4o"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_client.chat.completions.create.return_value = mock_response

        interceptor = OpenAIInterceptor(mock_client, tracker=tracker_obj, team_id="test")
        result = interceptor.chat_completions_create(model="gpt-4o", messages=[{"role": "user", "content": "hi"}])
        assert result is mock_response
        spend = tracker_obj.get_total_spend(team_id="test", period="all")
        assert spend > 0

    def test_anthropic_interceptor(self, tmp_db):
        tracker_obj = UsageTracker(db_path=tmp_db)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.usage.input_tokens = 200
        mock_response.usage.output_tokens = 100
        mock_client.messages.create.return_value = mock_response

        interceptor = AnthropicInterceptor(mock_client, tracker=tracker_obj, team_id="test")
        result = interceptor.messages_create(model="claude-sonnet-4-20250514", messages=[{"role": "user", "content": "hi"}])
        assert result is mock_response
        spend = tracker_obj.get_total_spend(team_id="test", period="all")
        assert spend > 0


# ── CLI Integration Tests ──────────────────────────────────────────────────

class TestCLI:
    def test_estimate_command(self, capsys):
        from aicostguard.cli import cmd_estimate
        args = MagicMock(provider="openai", model="gpt-4o", input_tokens=10000, output_tokens=5000)
        cmd_estimate(args)
        out = capsys.readouterr().out
        assert "0.075" in out  # 10000/1000 * 0.0025 + 5000/1000 * 0.010 = 0.075

    def test_prices_command(self, capsys):
        from aicostguard.cli import cmd_prices
        args = MagicMock()
        cmd_prices(args)
        out = capsys.readouterr().out
        assert "gpt-4o" in out
        assert "claude" in out.lower()
        assert "gemini" in out.lower()
