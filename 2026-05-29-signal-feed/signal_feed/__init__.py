"""Signal Feed — AI-Powered Market Signal Aggregator API

Collects and scores market signals from news RSS feeds, Reddit sentiment,
and public on-chain data. Exposes a REST API + WebSocket for real-time feeds.

Monetization: Free tier (5 req/min), Pro tier (100 req/min + WebSocket),
Enterprise (unlimited + custom sources).
"""

import os

__version__ = "0.1.0"

# Config
class Settings:
    """App settings from environment."""
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./signal_feed.db")
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL", "300"))
    API_KEY_HEADER: str = "X-API-Key"

settings = Settings()
