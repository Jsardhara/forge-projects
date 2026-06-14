# RegShield — AI Compliance & Regulatory Shield Platform

**Track AI model regulatory status by jurisdiction. Get alerts when restrictions change.**

Born from the June 2026 regulatory explosion: US government shut down Anthropic's Fable 5 and Mythos 5 globally, OpenAI faces state AG investigations, India lost access to frontier models, and Chinese AI models (GLM 5.2, DeepSeek) are trending but compliance-fragmented.

RegShield answers one critical question: **"Is [model] available in [country] for [use case]?"**

## Features

- **Model Registry** — 16 AI models tracked (OpenAI, Anthropic, Google, Meta, DeepSeek, GLM, Qwen, Mistral)
- **Compliance Checker** — API endpoint to check model availability by jurisdiction + use case
- **Real Regulatory Data** — Seeded from actual June 2026 events (Anthropic shutdown, OpenAI AG investigation, India access loss, Chinese model restrictions)
- **Alert System** — Active alerts for regulatory changes with acknowledgment
- **Audit Log** — Every compliance check is logged for legal defense
- **Web Dashboard** — Clean, professional UI with interactive compliance checker

## Quick Start

```bash
# Install
cd 2026-06-14-regshield
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Start server
uvicorn regshield.api:app --reload --port 8000
```

Then open http://localhost:8000 for the dashboard.

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `GET /api/models` | List all tracked models |
| `GET /api/models/{id}` | Get model details |
| `GET /api/check?model_id=X&jurisdiction=Y&use_case=Z` | Check compliance |
| `GET /api/statuses` | List regulatory statuses (filterable) |
| `GET /api/alerts` | List alerts |
| `POST /api/alerts/{id}/acknowledge` | Acknowledge alert |
| `GET /api/audit-log` | View audit trail |
| `GET /` | Web dashboard |

## Example

```bash
# Check if Claude Fable 5 is available in the US
curl "http://localhost:8000/api/check?model_id=anthropic/claude-fable-5&jurisdiction=US"

# Response:
# {
#   "model_id": "anthropic/claude-fable-5",
#   "model_name": "Claude Fable 5",
#   "jurisdiction": "US",
#   "risk_level": "banned",
#   "is_allowed": false,
#   "restrictions": ["US government ordered global shutdown June 2026", ...],
#   ...
# }
```

## Architecture

```
src/regshield/
├── __init__.py      # Package init
├── models.py        # Pydantic data models
├── store.py         # In-memory data store with seed data
├── api.py           # FastAPI application
└── templates.py     # Dashboard HTML renderer

tests/
├── test_models.py   # Model unit tests
├── test_store.py    # Store + compliance logic tests
└── test_api.py      # API endpoint tests
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic
- **Frontend**: Server-rendered HTML with vanilla JS (no build step)
- **Testing**: pytest
- **Packaging**: Hatchling

## Roadmap

- [ ] PostgreSQL backend for production persistence
- [ ] Webhook notifications for regulatory changes
- [ ] Hallucination risk scoring for AI outputs
- [ ] Multi-tenant support with org/workspace isolation
- [ ] Stripe billing integration ($49-299/mo tiers)
- [ ] Browser extension for real-time content scanning

## License

MIT
