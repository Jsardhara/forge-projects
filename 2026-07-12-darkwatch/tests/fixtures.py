"""Test fixtures (HTML strings) for darkwatch rules."""
from __future__ import annotations

# ---- Clean (compliant) page: newsletter checkbox OFF, clear cancel, no dark patterns
CLEAN_HTML = """
<!doctype html>
<html><head><title>Clean SaaS</title></head>
<body>
  <h1>Join our newsletter</h1>
  <form>
    <label><input type="checkbox" name="news"> Subscribe to our newsletter</label>
    <button type="submit">Sign up</button>
  </form>
  <p>To cancel your plan, visit <a href="/account/cancel">our cancel page</a> anytime.</p>
  <footer>We do not use auto-renewal by default.</footer>
</body></html>
"""

# ---- Roach-motel: signup but cancel only via phone call, no cancel link
ROACH_MOTEL_HTML = """
<!doctype html>
<html><head><title>Trapped</title></head>
<body>
  <h1>Start your membership</h1>
  <button>Subscribe now</button>
  <p>To cancel your subscription, call us at 1-800-555-0199 between 9-5.</p>
</body></html>
"""

# ---- Pre-checked consent checkbox
PRECHECKED_HTML = """
<!doctype html>
<html><head><title>Prechecked</title></head>
<body>
  <form>
    <label><input type="checkbox" name="marketing" checked> Subscribe to marketing offers</label>
    <button>Create account</button>
  </form>
</body></html>
"""

# ---- Forced continuity: free trial + auto-renew, no negation disclosure
FORCED_CONTINUITY_HTML = """
<!doctype html>
<html><head><title>Trial</title></head>
<body>
  <h1>Start your free trial</h1>
  <p>Your subscription renews automatically after the trial ends.</p>
  <button>Begin free trial</button>
</body></html>
"""

# ---- Forced continuity WITH clear negation (should be clean)
FORCED_CONTINUITY_CLEAN_HTML = """
<!doctype html>
<html><head><title>Trial</title></head>
<body>
  <h1>Start your free trial</h1>
  <p>No automatic renewal: we will never charge you without asking.</p>
  <button>Begin free trial</button>
</body></html>
"""

# ---- Confusing language
CONFUSING_HTML = """
<!doctype html>
<html><head><title>Confuse</title></head>
<body>
  <p>When you unsubscribe you will be charged a final processing fee.</p>
</body></html>
"""

# ---- Fake urgency / scarcity + countdown
FAKE_URGENCY_HTML = """
<!doctype html>
<html><head><title>Urgent</title></head>
<body>
  <div class="countdown">Offer ends tonight!</div>
  <p>Only 3 spots left!</p>
  <script>setInterval(() => tick(), 1000);</script>
</body></html>
"""

# ---- Mismatched consent: marketing box labeled only "terms"
MISMATCHED_HTML = """
<!doctype html>
<html><head><title>Mismatch</title></head>
<body>
  <form>
    <input type="checkbox" name="promo" checked>
    <label>I accept the terms and conditions</label>
    <button>Continue</button>
  </form>
</body></html>
"""

# ---- Disguised ad: sponsored element without "advertisement" disclosure
DISGUISED_AD_HTML = """
<!doctype html>
<html><head><title>Feed</title></head>
<body>
  <div class="sponsored">Buy the new gadget here!</div>
  <article>Real editorial content.</article>
</body></html>
"""

# ---- Minor-addictive engagement loops (no age gate)
MINOR_ADDICTIVE_HTML = """
<!doctype html>
<html><head><title>Loop</title></head>
<body>
  <h2>Claim your daily reward</h2>
  <p>Keep your streak bonus going by logging in every day!</p>
  <button>Spin to win</button>
</body></html>
"""

# ---- Minor-addictive WITH age gate (should be clean)
MINOR_ADDICTIVE_CLEAN_HTML = """
<!doctype html>
<html><head><title>Loop</title></head>
<body>
  <p>Must be 18+ to use this site.</p>
  <h2>Claim your daily reward</h2>
  <button>Spin to win</button>
</body></html>
"""

# ---- Heavy page that should trip NON_COMPLIANT (>=3 findings, multiple regs)
HEAVY_HTML = """
<!doctype html>
<html><head><title>Worst</title></head>
<body>
  <button>Start your free trial</button>
  <p>Your subscription renews automatically.</p>
  <p>Only 2 seats left! Hurry, offer ends tonight!</p>
  <div class="countdown">00:00:00</div>
  <label><input type="checkbox" name="marketing" checked> Subscribe to offers</label>
  <p>When you unsubscribe you will be charged a fee.</p>
</body></html>
"""
