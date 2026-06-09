# Forge Analytics

Build pipeline intelligence for the Jarmes multi-agent system.

## What It Does

Reads structured JSONL state files from `/jarvis/state/` and produces analytics reports on:
- **Build success rate** — how many builds succeed vs fail over time
- **Cost trends** — average, median, and total build costs
- **Duration trends** — how build times are changing
- **Error analysis** — most common failure patterns
- **Actionable recommendations** — data-driven suggestions for improving the build pipeline

## Quick Start

```bash
# Install
cd /c/Users/jyot2/jarvis/projects/forge-projects-repo/2026-06-09-forge-analytics
pip install -e ".[dev]"

# Generate a Markdown report
forge-analytics report

# Generate JSON output
forge-analytics report --json-output

# Filter by date range
forge-analytics report --since 2026-06-01 --until 2026-06-09

# Quick status
forge-analytics status

# Save report to file
forge-analytics report -o /c/Users/jyot2/jarvis/state/weekly-report.md
```

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for full details.

### Data Sources
- `daily_projects.jsonl` — build run metadata (cost, duration, status, errors)
- `forge_runs.jsonl` — forge run entries
- `cost_log.jsonl` — cost tracking per agent/action
- `sentinel_health.jsonl` — system health checks

### Output Formats
- **Markdown** — human-readable report with tables, trends, and recommendations
- **JSON** — machine-readable for the agent bus or API consumption

## Running Tests

```bash
pytest tests/ -v
```

## Known Limitations
- Reads JSONL files directly (no database) — may be slow with very large files
- Date filtering is string-based (YYYY-MM-DD format)
- No real-time streaming — snapshot analysis only

## Next Steps
- Add support for `cost_log.jsonl` analysis
- Add trend alerts (e.g., "costs increased 50% this week")
- Integrate with agent bus for automated reporting
