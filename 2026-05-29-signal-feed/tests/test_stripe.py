"""Tests for Stripe payment integration."""

import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def stripe_env(monkeypatch):
    """Set Stripe env vars before each test."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_PUBLISHABLE_KEY", "pk_test_fake")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_fake")
    monkeypatch.setenv("STRIPE_PRICE_PRO", "price_fake_pro")
    monkeypatch.setenv("STRIPE_PRICE_ENTERPRISE", "price_fake_enterprise")
    # Force reimport of module to pick up env vars
    import importlib
    import signal_feed.stripe_payments
    importlib.reload(signal_feed.stripe_payments)


class TestTiers:
    def test_free_tier(self):
        from signal_feed.stripe_payments import get_tier
        tier = get_tier("free")
        assert tier["price"] == 0

    def test_pro_tier(self):
        from signal_feed.stripe_payments import get_tier
        tier = get_tier("pro")
        assert tier["price"] == 19

    def test_enterprise_tier(self):
        from signal_feed.stripe_payments import get_tier
        tier = get_tier("enterprise")
        assert tier["price"] == 99

    def test_invalid_tier_defaults_to_free(self):
        from signal_feed.stripe_payments import get_tier
        tier = get_tier("nonexistent")
        assert tier["price"] == 0

    def test_all_tiers_have_features(self):
        from signal_feed.stripe_payments import TIERS
        for tid, info in TIERS.items():
            assert len(info["features"]) > 0


class TestCheckout:
    @patch("signal_feed.stripe_payments.stripe.checkout.Session.create")
    def test_create_checkout_pro(self, mock_create):
        from signal_feed.stripe_payments import create_checkout_session
        mock_create.return_value = MagicMock(url="https://checkout.stripe.com/test", id="cs_test_123")
        result = create_checkout_session("pro", "user@example.com", "https://ok.com", "https://cancel.com")
        assert result["tier"] == "pro"
        assert "checkout.stripe.com" in result["url"]

    @patch("signal_feed.stripe_payments.stripe.checkout.Session.create")
    def test_create_checkout_enterprise(self, mock_create):
        from signal_feed.stripe_payments import create_checkout_session
        mock_create.return_value = MagicMock(url="https://checkout.stripe.com/test", id="cs_test_456")
        result = create_checkout_session("enterprise", "user@example.com", "https://ok.com", "https://cancel.com")
        assert result["tier"] == "enterprise"

    def test_free_tier_returns_no_url(self):
        from signal_feed.stripe_payments import create_checkout_session
        result = create_checkout_session("free", "user@example.com", "https://ok.com", "https://cancel.com")
        assert result["tier"] == "free"
        assert result["url"] is None

    def test_checkout_without_price_id_raises(self):
        from signal_feed.stripe_payments import create_checkout_session, TIERS
        original = TIERS["pro"]["stripe_price_id"]
        TIERS["pro"]["stripe_price_id"] = None
        try:
            with pytest.raises(ValueError, match="No Stripe price ID"):
                create_checkout_session("pro", "user@example.com", "https://ok.com", "https://cancel.com")
        finally:
            TIERS["pro"]["stripe_price_id"] = original
