# Signal Feed — AI-Powered Market Signal Aggregator API

Collects and scores real-time market signals from crypto news, stock market news, Reddit sentiment, and social buzz. Exposes a clean REST API + WebSocket.

## Quick Start

```bash
# Install dependencies (using uv)
cd /c/Users/jyot2/jarvis/projects/signal-feed
uv sync

# Run the server
uv run signal-feed
# Or equivalently:
uv run python -m signal_feed.api
```

Server starts at `http://localhost:8000`.

## API Usage

All endpoints require the `X-API-Key` header. Use `sf-demo-key-2026` for free tier.

### Trigger a collection run
```bash
curl -X POST http://localhost:8000/api/v1/collect/trigger \
  -H "X-API-Key: sf-demo-key-2026"
```

### Get all signals
```bash
curl http://localhost:8000/api/v1/signals \
  -H "X-API-Key: sf-demo-key-2026"
```

### Get crypto signals only
```bash
curl "http://localhost:8000/api/v1/signals?category=crypto&limit=20" \
  -H "X-API-Key: sf-demo-key-2026"
```

### Get top bullish signals
```bash
curl http://localhost:8000/api/v1/signals/top?direction=bullish&limit=10 \
  -H "X-API-Key: sf-demo-key-2026"
```

### Sentiment overview dashboard
```bash
curl http://localhost:8000/api/v1/sentiment/overview \
  -H "X-API-Key: sf-demo-key-2026"
```

### WebSocket (live stream)
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/v1/live");
ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

## API Docs

Interactive Swagger docs at `http://localhost:8000/docs`

## Running Tests

```bash
uv run pytest tests/ -v
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  RSS Feeds   │────▶│              │────▶│  REST API    │
│  Reddit JSON │────▶│  Collector   │────▶│  WebSocket   │
│  (future:    │────▶│  + Analyzer  │────▶│  Dashboard   │
│   on-chain)  │     │              │     │              │
└─────────────┘     └──────────────┘     └──────────────┘
                           │
                    ┌──────▼──────┐
                    │  SQLite DB  │
                    │  (async)    │
                    └─────────────┘
```

## Tech Stack
- **Python 3.14** + **FastAPI** for the API server
- **httpx** for async HTTP collection
- **feedparser** for RSS parsing
- **SQLAlchemy 2.0** + **aiosqlite** for async database
- **structlog** for structured logging
- **pytest** for testing

## Future Enhancements
- [ ] CoinGecko/CoinMarketCap API integration for price signals
- [ ] Twitter/X API for social sentiment
- [ ] FinBERT/CryptoBERT for ML-based sentiment (replace keyword scoring)
- [ ] Redis for real-time pub/sub between collector and API
- [ ] Rate limiting middleware per tier
- [ ] Webhook delivery (POST signals to subscriber URLs)
- [ ] Admin dashboard (Next.js frontend)
