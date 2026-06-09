# Architecture: Forge Analytics

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    forge-analytics                       │
│                                                         │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │  DataLayer   │──▶│  Analytics   │──▶│  Reporter    │ │
│  │  (readers)   │   │  (compute)   │   │  (output)    │ │
│  └─────────────┘   └──────────────┘   └──────────────┘ │
│         │                  │                  │         │
│         ▼                  ▼                  ▼         │
│  forge_runs.jsonl   Aggregations      Markdown report   │
│  daily_projects.jsonl  Trends         JSON summary      │
│  cost_log.jsonl        Anomailes      Bus publish       │
│  sentinel_health.jsonl                                 │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack
- **Python 3.11+** — stdlib only + `statistics` module
- **No external dependencies** for core analytics (uses `json`, `datetime`, `pathlib`, `statistics` from stdlib)
- **Click** for CLI (lightweight, single-file, works without pip install if needed)
- **Hatchling** build backend for packaging

## File Structure
```
2026-06-09-forge-analytics/
  forge_analytics/
    __init__.py
    readers.py        # JSONL file readers with error resilience
    models.py         # Pydantic/dataclass models for run data
    analytics.py      # Trend computation, aggregation, anomaly detection
    reporter.py       # Markdown report generation
    cli.py            # Command-line interface
  tests/
    test_readers.py
    test_analytics.py
    test_reporter.py
    test_cli.py
    fixtures/         # Sample JSONL data for testing
  pyproject.toml
  README.md
  JUSTIFY.md
  (this file)
```

## Data Sources

### `forge_runs.jsonl`
Each line: `{run_id, repo_path, branch, task, status, timestamp, ...}`
- ~15 lines covering May–June 2026

### `daily_projects.jsonl`
Each line: `{ts, date, slug, title, folder, repo_url, commit_sha, cost_usd, duration_sec, status, error, spec}`
- 9 lines covering May 4 – June 8

### `cost_log.jsonl`
Each line: cost tracking entries per agent/action

### `sentinel_health.jsonl`
Each line: health check results (5790 lines)

## Key Design Decisions

1. **No database** — read directly from JSONL files. Keeps the tool simple and portable.
2. **Defensive parsing** — JSONL files may have malformed lines. Skip and count, don't crash.
3. **Pluggable reporters** — Markdown for humans, JSON for agent bus.
4. **Date-first filtering** — most queries are time-range based.
5. **Stateless** — no persistence between runs. Idempotent.

## Failure Modes
- Missing JSONL files → warning + empty dataset (don't crash)
- Malformed JSON lines → skip + count in report stats
- Empty date range → report says "no data"
- Permission errors on state files → clear error message
