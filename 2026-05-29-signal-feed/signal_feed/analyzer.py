"""Keyword-based sentiment analysis — no ML dependencies required.

Uses curated keyword lists + simple heuristics for fast, deterministic
signal scoring. Good enough for MVP; swap for FinBERT/CryptoBERT in pro.
"""

# Keywords weighted by conviction strength
BULLISH_KEYWORDS = {
    # strong
    "surge": 0.8, "soar": 0.9, "rocket": 0.9, "breakout": 0.8, "moon": 0.7,
    "all-time high": 0.9, "ath": 0.8, "bull run": 0.8, "rally": 0.7,
    "accumulate": 0.6, "buy the dip": 0.7, "undervalued": 0.6,
    "adoption": 0.5, "partnership": 0.5, "institutional": 0.6,
    "upgrade": 0.6, "approved": 0.7, "approval": 0.7,
    "outperform": 0.7, "beat expectations": 0.7, "strong earnings": 0.7,
    "rate cut": 0.6, "dovish": 0.5, "stimulus": 0.6,
    "short squeeze": 0.8, "gamma squeeze": 0.8,
}

BEARISH_KEYWORDS = {
    # strong
    "crash": -0.9, "collapse": -0.9, "plunge": -0.8, "dump": -0.8,
    "hack": -0.8, "exploit": -0.8, "rug pull": -0.9, "scam": -0.7,
    "bankrupt": -0.9, "bankruptcy": -0.9, "liquidated": -0.7,
    "ban": -0.7, "crackdown": -0.7, "sec investigation": -0.7,
    "overvalued": -0.6, "bubble": -0.6, "correction": -0.5,
    "inflation": -0.5, "rate hike": -0.6, "hawkish": -0.5,
    "layoff": -0.5, "recession": -0.7, "defaults": -0.7,
    "missed expectations": -0.7, "downgrade": -0.6,
    "sell-off": -0.7, "capitulation": -0.8, "fear": -0.5,
    "frozen": -0.6, "withdrawal halted": -0.8,
}

CRYPTO_CATEGORIES = {
    "bitcoin": "crypto", "btc": "crypto", "ethereum": "crypto", "eth": "crypto",
    "solana": "crypto", "sol": "crypto", "defi": "crypto", "nft": "crypto",
    "token": "crypto", "altcoin": "crypto", "stablecoin": "crypto",
    "layer2": "crypto", "l2": "crypto", "blockchain": "crypto",
}

STOCK_CATEGORIES = {
    "stock": "stocks", "shares": "stocks", "equity": "stocks", "s&p": "stocks",
    "nasdaq": "stocks", "dow": "stocks", "nyse": "stocks", "ipo": "stocks",
    "earnings": "stocks", "dividend": "stocks", "futures": "stocks",
}


def classify_category(text: str) -> str:
    """Classify text into a market category."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in CRYPTO_CATEGORIES):
        return "crypto"
    if any(kw in text_lower for kw in STOCK_CATEGORIES):
        return "stocks"
    return "general"


def score_sentiment(text: str) -> tuple[float, str]:
    """
    Score sentiment of text. Returns (score, label).
    Score range: -1.0 (extremely bearish) to +1.0 (extremely bullish).
    """
    text_lower = text.lower()
    score = 0.0
    matches = 0

    for keyword, weight in BULLISH_KEYWORDS.items():
        if keyword in text_lower:
            score += weight
            matches += 1

    for keyword, weight in BEARISH_KEYWORDS.items():
        if keyword in text_lower:
            score += weight  # weight is already negative
            matches += 1

    if matches == 0:
        return 0.0, "neutral"

    # Normalize to [-1, 1]
    normalized = max(-1.0, min(1.0, score / matches))

    if normalized > 0.2:
        label = "bullish"
    elif normalized < -0.2:
        label = "bearish"
    else:
        label = "neutral"

    return round(normalized, 3), label
