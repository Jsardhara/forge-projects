"""Stripe payment integration for Signal Feed."""

import os
import stripe

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
STRIPE_PUBLISHABLE_KEY = os.environ["STRIPE_PUBLISHABLE_KEY"]
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

TIERS = {
    "free": {
        "name": "Free",
        "price": 0,
        "price_display": "Free",
        "requests_per_minute": 5,
        "features": ["Public signals", "Basic search"],
    },
    "pro": {
        "name": "Pro",
        "price": 19,
        "price_display": "$19/mo",
        "requests_per_minute": 100,
        "features": ["All signals", "WebSocket", "Priority support"],
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO", "price_1TdGN2462Oake79BimmxI78h"),
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 99,
        "price_display": "$99/mo",
        "requests_per_minute": 1000,
        "features": ["Everything in Pro", "Webhooks", "Custom integrations", "Dedicated support"],
        "stripe_price_id": os.getenv("STRIPE_PRICE_ENTERPRISE", "price_1TdGN3462Oake79BEKJYRJ7P"),
    },
}


def get_tier(tier_id: str) -> dict:
    return TIERS.get(tier_id, TIERS["free"])


def create_checkout_session(tier_id: str, customer_email: str, success_url: str, cancel_url: str) -> dict:
    """Create a Stripe Checkout session for subscription signup."""
    tier = get_tier(tier_id)
    if tier_id == "free":
        return {"tier": "free", "url": None}

    price_id = tier.get("stripe_price_id")
    if not price_id:
        raise ValueError(
            f"No Stripe price ID for tier '{tier_id}'. "
            "Create a price in Stripe dashboard and set STRIPE_PRICE_PRO env var."
        )

    session = stripe.checkout.Session.create(
        customer_email=customer_email,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"tier": tier_id},
    )
    return {"tier": tier_id, "url": session.url, "session_id": session.id}


def create_customer_portal_session(customer_id: str, return_url: str) -> str:
    """Create a Stripe Customer Portal session for managing subscription."""
    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return session.url


def verify_webhook(payload: bytes, sig_header: str) -> dict:
    """Verify a Stripe webhook event."""
    if not STRIPE_WEBHOOK_SECRET:
        raise ValueError("STRIPE_WEBHOOK_SECRET not configured")
    event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    return event
