# Architecture: AI Failbook

## System Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  CLI (Rich)  │────▶│              │     │             │
│  failbook    │     │   Store      │────▶│  SQLite DB  │
│  search      │     │   (Python)   │     │  failbook.db│
│  add         │     │              │     │             │
│  stats       │     │  - create    │     └─────────────┘
└─────────────┘     │  - get       │
                    │  - update    │
┌─────────────┐     │  - delete    │
│  REST API   │────▶│  - search    │
│  FastAPI    │     │  - stats     │
│  /failures  │     │  - seed      │
│  /stats     │     │              │
└─────────────┘     └──────────────┘
```

## Tech Stack Rationale

- **Python 3.11+**: Universal, no compilation, rich ecosystem
- **SQLite**: Zero-config, portable, single-file database. No server needed. Perfect for a CLI-first tool.
- **Pydantic v2**: Type-safe models with validation. Clean serialization for both CLI and API.
- **FastAPI**: Auto-generated OpenAPI docs, async support, Pydantic integration.
- **Click + Rich**: Best-in-class CLI framework with beautiful terminal output.
- **pytest**: Standard testing with fixtures and parametrize support.

## File Structure

```
ai-failbook/
├── ai_failbook/
│   ├── __init__.py      # Package version
│   ├── models.py        # Pydantic models (FailureMode, SearchQuery, etc.)
│   ├── store.py         # SQLite storage layer
│   ├── api.py           # FastAPI REST endpoints
│   └── cli.py           # Click CLI with Rich output
├── tests/
│   └── test_failbook.py # Comprehensive test suite
├── pyproject.toml       # Hatchling build, deps, scripts
├── JUSTIFY.md           # Why this project exists
├── ARCHITECTURE.md      # This file
└── README.md            # Quick start and usage
```

## Key Design Decisions

1. **SQLite over Postgres**: This is a single-user/local-first tool. SQLite eliminates setup friction. Can migrate to Postgres later if multi-user needed.

2. **In-memory for tests**: All tests use `:memory:` SQLite — fast, isolated, no cleanup needed.

3. **vid not id**: Field named `vid` not `id` to avoid shadowing Python's built-in `id()` function (learned from forge-profile pitfall).

4. **Append-only upvotes**: Upvotes are atomic increments, not separate table. Simpler, sufficient for this use case.

5. **Tags as JSON array in SQLite**: SQLite has no native JSON array type. Tags stored as JSON string, parsed on read. Good enough for <10K entries.

6. **Seed data on first API startup**: The API lifespan handler checks if DB is empty and seeds 8 real-world failures. CLI has explicit `seed` command.

## Failure Categories

| Category | Description |
|----------|-------------|
| hallucination | Model generates false information confidently |
| instruction_following | Model doesn't follow or over-follows instructions |
| context_window | Failures related to context length limits |
| safety_refusal | Over-refusal or under-refusal of requests |
| tool_use | Failures in API/tool calling |
| reasoning | Logical errors, math mistakes |
| code_generation | Vulnerable or incorrect code output |
| prompt_injection | External instructions hijack the model |
| cost_token | Unexpected token usage/cost spikes |
| latency | Performance degradation issues |
| data_leak | PII or sensitive data in outputs |
| other | Uncategorized failures |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API info and endpoint list |
| GET | `/failures` | Search with filters (q, category, severity, model, tag) |
| GET | `/failures/{vid}` | Get single failure mode |
| POST | `/failures` | Create new failure mode |
| PATCH | `/failures/{vid}` | Update failure mode |
| DELETE | `/failures/{vid}` | Delete failure mode |
| POST | `/failures/{vid}/upvote` | Upvote a failure mode |
| GET | `/stats` | Aggregate statistics |
| GET | `/categories` | List all categories |
| GET | `/severities` | List all severity levels |

## Rollback Plan
- SQLite DB is a single file — back it up, restore it.
- No migrations yet (v0.1.0). If schema changes, recreate DB and re-seed.
- API is stateless — restart with different DB path to switch versions.
