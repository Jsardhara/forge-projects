# Architecture: Jarmes Health Pulse

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Jarmes Health Pulse                   │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │  Log Parser   │───▶│  Aggregator  │───▶│  FastAPI  │ │
│  │  (tail/parse) │    │  (group/count)│    │  Server   │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│         │                    │                  │       │
│         ▼                    ▼                  ▼       │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │ sentinel.log  │    │  In-memory   │    │  Dashboard │ │
│  │ jarvis_api.log│    │  state       │    │  (HTML)    │ │
│  │ uvicorn.log   │    │  (dicts)     │    │            │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Auto-Fix Suggester                   │   │
│  │  Known patterns → suggested fixes                 │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack Rationale
- **Python 3.11+ (Hermes venv)**: Already available, no new installs needed
- **FastAPI**: Already in the Hermes ecosystem, async, auto-docs
- **stdlib only for parsing**: No new dependencies for log parsing
- **Pure HTML dashboard**: No JS framework needed — keeps it lightweight
- **No database**: In-memory state is sufficient for log analysis

## File Structure
```
2026-06-05-jarmes-health-pulse/
  healthpulse/
    __init__.py
    parser.py        # Log file parser (tail, regex, extract)
    aggregator.py    # Error grouping, counting, trending
    models.py        # Pydantic models for health state
    suggester.py     # Auto-fix suggestions for known patterns
    server.py        # FastAPI app + dashboard HTML
    cli.py           # CLI entry point
  tests/
    test_parser.py
    test_aggregator.py
    test_models.py
    test_suggester.py
  pyproject.toml
  README.md
  JUSTIFY.md
  ARCHITECTURE.md
```

## Key Design Decisions
1. **Log parsing over instrumentation**: We can't modify the Jarmes daemon to emit metrics. Parsing existing logs is the only non-invasive option.
2. **In-memory state**: No database needed. Logs are re-parsed on startup. State is ephemeral by design.
3. **Regex-based extraction**: APScheduler log format is consistent. Regex is faster and simpler than structured logging.
4. **Known-pattern matching**: A small dictionary of regex → fix suggestions covers the most common errors.

## Failure Modes
- **Log file not found**: Graceful degradation — show "no data" for that source
- **Malformed log lines**: Skip and count as "unparseable"
- **Large log files**: Read last N lines only (configurable, default 5000)
- **Port in use**: Fall back to port+1

## Rollback
Delete the project folder. No system files are modified. No services are installed.
