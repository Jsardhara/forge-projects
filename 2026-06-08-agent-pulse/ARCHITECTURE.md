# Architecture: AgentPulse

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    AgentPulse Dashboard                  │
│                  (HTML + JS, 30s refresh)                │
├─────────────────────────────────────────────────────────┤
│  FastAPI Backend (:8765)                                │
│  ├── GET /api/agents      → agent_log.jsonl             │
│  ├── GET /api/builds      → daily_projects.jsonl        │
│  ├── GET /api/health      → sentinel_health.jsonl       │
│  ├── GET /api/costs       → cost_log.jsonl              │
│  ├── GET /api/bus         → bus inbox                   │
│  └── GET /api/stats       → aggregated summary          │
├─────────────────────────────────────────────────────────┤
│  Data Sources (read-only)                               │
│  C:\Users\jyot2\jarvis\state\*.jsonl                    │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack
- **Backend**: Python 3.14 + FastAPI (already available on host)
- **Frontend**: Vanilla HTML + CSS + JavaScript (no build step, no npm)
- **Data**: JSONL files read directly from disk
- **Deployment**: Local FastAPI server on port 8765

## Why Not Next.js?
- No npm/next on this host without `env -u PYTHONHOME` prefix (pitfall)
- No build step needed — this is a local monitoring dashboard
- Vanilla HTML/JS is faster to build and maintain for this use case
- No auth needed (localhost only)

## File Structure
```
agent-pulse/
  .gitignore
  JUSTIFY.md
  ARCHITECTURE.md
  README.md
  pyproject.toml
  src/
    __init__.py
    main.py          # FastAPI app + routes
    readers.py       # JSONL file readers
    models.py        # Pydantic models
  static/
    index.html       # Dashboard HTML
    style.css        # Dashboard styles
    app.js           # Dashboard JS
  tests/
    test_readers.py
    test_models.py
    test_api.py
```

## Key Design Decisions
1. **Read-only**: Never writes to state files. Pure monitoring.
2. **30s polling**: Frontend refreshes every 30s. No WebSocket complexity.
3. **Tailwind CDN**: Use Tailwind via CDN for styling (no build step).
4. **File watching**: Use file mtime to avoid re-reading unchanged files.
5. **Error resilience**: Missing files return empty arrays, not 500s.

## Failure Modes
- State files missing → return empty data, log warning
- Corrupt JSONL lines → skip line, count errors
- Port 8765 in use → fail fast with clear message
- Large files → read last N lines only (configurable, default 100)
