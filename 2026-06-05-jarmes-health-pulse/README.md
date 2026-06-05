# Jarmes Health Pulse

**Lightweight log-based system health dashboard for the Jarmes multi-agent system.**

## The Problem

The Jarmes multi-agent system runs 12+ scheduled cron jobs via APScheduler. When jobs fail, errors go to `sentinel.log` — an 8,496-line, 913KB file that's impossible to read manually. Recurring errors (like `sync_tick`'s pydantic ValidationError repeating every 30 seconds for 32 days) go unnoticed.

## What This Does

1. **Parses** sentinel.log and other Jarmes log files
2. **Aggregates** errors by job, error type, and time window
3. **Shows** per-job health status (healthy / degraded / failing)
4. **Detects** recurring failure patterns with counts
5. **Suggests** auto-fixes for known error patterns
6. **Serves** a dark-themed web dashboard at `http://localhost:8742`

## Quick Start

```bash
# Install
cd 2026-06-05-jarmes-health-pulse
uv pip install -e ".[dev]"

# CLI summary
healthpulse summary

# Start dashboard
healthpulse serve --port 8742
```

## Architecture

- `healthpulse/parser.py` — Log file parser (regex-based, reads last N lines)
- `healthpulse/aggregator.py` — Error grouping, counting, trending
- `healthpulse/models.py` — Pydantic models for health state
- `healthpulse/suggester.py` — Auto-fix suggestions for known patterns
- `healthpulse/server.py` — FastAPI app + dashboard HTML
- `healthpulse/cli.py` — CLI entry point

## API

- `GET /` — Dashboard (HTML)
- `GET /api/health?max_lines=5000` — Full health JSON
- `GET /api/health/summary` — Quick summary

## Known Limitations

- In-memory state only (no persistence)
- Regex-based parsing (may miss non-standard log formats)
- Reads from local filesystem only (no remote log shipping)
- Single-machine only

## Next Steps

- [ ] Add log file rotation awareness
- [ ] Add alerting (Discord webhook on new failures)
- [ ] Add historical trending (store snapshots)
- [ ] Add config file for log paths and patterns
