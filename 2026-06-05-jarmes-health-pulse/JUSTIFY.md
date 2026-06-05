# Project Justification: Jarmes Health Pulse

## Problem
The Jarmes multi-agent system runs 12+ scheduled cron jobs (email_tick, calendar_tick, sync_tick, heartbeat_tick, atlas_tick, etc.) via APScheduler. When these jobs fail, errors are logged to `sentinel.log` — an 8,496-line, 913KB file that's impossible to read manually. The operator has no visibility into which jobs are healthy, which are failing, or how often. Errors like the `sync_tick` pydantic ValidationError (Task status 'completed' doesn't match pattern) repeat every 30 seconds, flooding the log, but nobody knows until they manually grep it.

## Existing Solutions
- **Manual log greps**: `grep ERROR sentinel.log` — works but shows raw lines, no aggregation, no trends, no job-level health
- **ELK/Splunk**: Massive overkill for a single-machine agent system
- **Prometheus + Grafana**: Requires instrumenting every job with metrics — the Jarmes system doesn't have this
- **No existing tool**: There's no lightweight, log-file-based health dashboard for Python APScheduler setups

## Proposed Solution
**Jarmes Health Pulse** — a single-file Python log parser + FastAPI dashboard that:
1. Tails `sentinel.log` and other Jarmes log files
2. Aggregates errors by job, error type, and time window
3. Shows per-job health status (healthy / degraded / failing)
4. Detects recurring failure patterns and suggests fixes
5. Serves a lightweight web dashboard at `http://localhost:8742`
6. Zero dependencies beyond FastAPI + stdlib — runs on the Hermes venv

## Impact Criteria
- Operator can see system health in <5 seconds (vs. manual grep)
- Recurring errors are surfaced with counts and first-seen timestamps
- Auto-fix suggestions for known error patterns (e.g., the Task status mismatch)
- Deployable in <1 minute: `python -m healthpulse serve`

## Why now
The sentinel.log is already 913KB with 8,496 lines. It will only grow. The `sync_tick` error has been repeating since May 4th. Today is June 5th — that's 32 days of unnoticed failures. This tool would have caught it on day 1.
