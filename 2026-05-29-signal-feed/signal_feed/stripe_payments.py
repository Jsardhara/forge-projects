"""Stripe integration for Signal Feed — checkout sessions, webhook handling, and subscription management."""

import hashlib
import hmac
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — populated from environment / settings
# ---------------------------------------------------------------------------
STRIPE_SECRET_KEY: str = ""          # sk_live_... or sk_test_...
STRIPE_WEBHOOK_SECRET: str = ""      # whsec_...
STRIPE_PRICE_PRO: str = ""           # price_... for $19/mo
STRIPE_PRICE_ENTERPRISE: str = ""    # price_... for $99/mo
BASE_URL: str = "http://localhost:8000"

router = APIRouter(prefix="/api/v1/stripe", tags=["stripe"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_prices() -> dict:
    prices = {}
    if STRIPE_PRICE_PRO:
        prices["pro"] = {"price_id": STRIPE_PRICE_PRO, "amount": 19, "interval": "month"}
    if STRIPE_PRICE_ENTERPRISE:
        prices["enterprise"] = {"price_id": STRIPE_PRICE_ENTERPRISE, "amount": 99, "interval": "month"}
    return prices


async def _stripe_post(path: str, data: dict) -> dict:
    """POST to Stripe API."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(500, "Stripe is not configured")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.stripe.com/v1/{path}",
            data=data,
            auth=(STRIPE_SECRET_KEY, ""),
            timeout=15,
        )
    return resp.json()


async def _stripe_get(path: str) -> dict:
    """GET from Stripe API."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(500, "Stripe is not configured")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.stripe.com/v1/{path}",
            auth=(STRIPE_SECRET_KEY, ""),
            timeout=15,
        )
    return resp.json()


# ---------------------------------------------------------------------------
# Public endpoint: available plans
# ---------------------------------------------------------------------------
@router.get("/plans")
async def list_plans():
    """Return available subscription plans."""
    plans = []
    for tier, info in _get_prices().items():
        plans.append({
            "tier": tier,
            "amount_usd": info["amount"],
            "interval": info["interval"],
            "features": _tier_features(tier),
        })
    return {"plans": plans}


def _tier_features(tier: str) -> list[str]:
    features = {
        "free": ["5 requests/min", "REST API", "24h data history"],
        "pro": ["100 requests/min", "REST API + WebSocket", "30d data history", "10 webhooks"],
        "enterprise": ["Unlimited requests", "REST API + WebSocket", "Unlimited history", "Unlimited webhooks", "Custom sources", "Priority support"],
    }
    return features.get(tier, [])


# ---------------------------------------------------------------------------
# Create checkout session
# ---------------------------------------------------------------------------
@router.post("/checkout")
async def create_checkout(request: Request):
    """Create a Stripe checkout session for the requested tier."""
    body = await request.json()
    tier = body.get("tier", "pro")
    prices = _get_prices()
    if tier not in prices:
        raise HTTPException(400, f"Unknown tier: {tier}. Available: {list(prices)}")

    price_id = prices[tier]["price_id"]
    success_url = f"{BASE_URL}/docs?checkout=success"
    cancel_url = f"{BASE_URL}/docs?checkout=cancel"

    session = await _stripe_post("checkout/sessions", {
        "mode": "subscription",
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata[tier]": tier,
    })
    if "url" not in session:
        logger.error("Stripe checkout error: %s", session)
        raise HTTPException(500, "Stripe checkout creation failed")

    return {"checkout_url": session["url"], "session_id": session["id"]}


# ---------------------------------------------------------------------------
# Create customer portal session
# ---------------------------------------------------------------------------
@router.post("/portal")
async def create_portal(request: Request):
    """Create a Stripe billing portal session for the customer."""
    body = await request.json()
    customer_id = body.get("customer_id")
    if not customer_id:
        raise HTTPException(400, "customer_id is required")

    session = await _stripe_post("billing_portal/sessions", {
        "customer": customer_id,
        "return_url": f"{BASE_URL}/docs",
    })
    if "url" not in session:
        raise HTTPException(500, "Portal creation failed")
    return {"portal_url": session["url"]}


# ---------------------------------------------------------------------------
# Stripe webhook handler
# ---------------------------------------------------------------------------
@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events for subscription lifecycle."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Verify signature
    if STRIPE_WEBHOOK_SECRET:
        expected = hmac.new(
            STRIPE_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(f"v1={expected}", sig_header):
            raise HTTPException(400, "Invalid signature")

    event = (await request.json())
    etype = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    logger.info("[Stripe] Webhook event: %s", etype)

    if etype == "checkout.session.completed":
        customer_id = data.get("customer")
        tier = (data.get("metadata") or {}).get("tier", "pro")
        await _activate_subscription(customer_id, tier)

    elif etype == "customer.subscription.deleted":
        customer_id = data.get("customer")
        await _deactivate_subscription(customer_id)

    elif etype == "invoice.payment_failed":
        customer_id = data.get("customer")
        logger.warning("[Stripe] Payment failed for customer %s", customer_id)
        await _suspend_subscription(customer_id)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Subscription DB operations (simple file-based; replace with DB later)
# ---------------------------------------------------------------------------
import json as _json
from pathlib import Path

_SUBSCRIPTIONS_FILE = Path(__file__).parent.parent / "data" / "_subscriptions.json"


def _load_subs() -> dict:
    if _SUBSCRIPTIONS_FILE.exists():
        return _json.loads(_SUBSCRIPTIONS_FILE.read_text())
    return {}


def _save_subs(subs: dict):
    _SUBSCRIPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SUBSCRIPTIONS_FILE.write_text(_json.dumps(subs, indent=2, default=str))


async def _activate_subscription(customer_id: str, tier: str):
    subs = _load_subs()
    subs[customer_id] = {
        "tier": tier,
        "status": "active",
        "activated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_subs(subs)
    logger.info("[Stripe] Activated %s subscription for %s", tier, customer_id)


async def _deactivate_subscription(customer_id: str):
    subs = _load_subs()
    if customer_id in subs:
        subs[customer_id]["status"] = "cancelled"
        subs[customer_id]["cancelled_at"] = datetime.now(timezone.utc).isoformat()
        _save_subs(subs)
        logger.info("[Stripe] Deactivated subscription for %s", customer_id)


async def _suspend_subscription(customer_id: str):
    subs = _load_subs()
    if customer_id in subs:
        subs[customer_id]["status"] = "past_due"
        _save_subs(subs)


def get_subscription_tier(customer_id: str) -> str:
    """Return the subscription tier for a customer_id, or 'free'."""
    subs = _load_subs()
    sub = subs.get(customer_id)
    if sub and sub.get("status") == "active":
        return sub["tier"]
    return "free"
