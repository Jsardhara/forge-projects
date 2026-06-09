# Project Justification: Forge Analytics

## Problem
The Jarmes multi-agent system has been running daily autonomous builds since May 2026. Each run generates metadata: cost (USD), duration (seconds), status (success/failed/skipped), error messages, commit SHAs, and project specs. This data lives in JSONL files (`forge_runs.jsonl`, `daily_projects.jsonl`, `cost_log.jsonl`) in `/jarvis/state/` — and is never analyzed. The operator has no visibility into whether builds are getting faster, cheaper, more reliable, or more expensive over time. When a build fails, there's no systematic way to see if it's part of a pattern or a one-off.

## Existing Solutions
- **AgentPulse** (built June 8) gives a real-time dashboard of agent activity, but it reads JSONL files as-is without computing trends, aggregations, or recommendations.
- **Generic analytics tools** (Grafana, Metabase) require infrastructure the system doesn't have and don't understand the Jarmes-specific data schema.
- **Manual inspection** of JSONL files is error-prone and doesn't scale — the operator shouldn't grep logs to understand their own system's performance.

## Proposed Solution
`forge-analytics` — a Python CLI + library that:
1. Reads all structured JSONL state files from the Jarmes system
2. Computes build trends: cost/duration over time, success rate, error frequency
3. Identifies the most expensive builds, longest builds, and most common failure patterns
4. Generates a Markdown report suitable for posting to the agent bus or emailing to the operator
5. Supports `--since`, `--until`, `--agent`, and `--status` filters
6. Can be run as a cron job for weekly/monthly reporting

## Impact Criteria
- Successfully reads and parses all JSONL state files without errors
- Produces a report covering ≥90% of historical builds
- Identifies at least one actionable insight from existing data (e.g., "average build cost increased 40% over 2 weeks")
- Report is readable in plain text (Markdown) without requiring a browser

## Why now
The system has ~50 days of build history across 15+ projects. This is enough data to identify meaningful trends. Building analytics now scales from day one rather than retrofitting later. The operator explicitly prioritized self-improving tools (Category 1) — this is the most direct example: a tool that measures and improves the tool-building process itself.
