# 🛡️ AI Cost Guard

**Track, optimize, and control your team's AI API spending.**

AI Cost Guard monitors usage across OpenAI, Anthropic, and Google AI APIs. It detects waste, sets budgets, and alerts on anomalies — so you never get a surprise bill again.

## Why?

Teams using AI APIs are bleeding money:
- No visibility into who's spending what
- Expensive models used where cheap ones would do
- No budget alerts until the invoice arrives
- No way to allocate costs per team/project

AI Cost Guard fixes all of that.

## Features

- **📊 Real-time spend tracking** — SQLite-backed, tracks every API call with token counts and cost estimates
- **💰 Budget management** — Set daily/weekly/monthly budgets per provider, model, or team
- **🔔 Smart alerts** — Get warned at 80% of budget, alerted at 100%+
- **💡 Waste detection** — Automatically suggests cheaper model alternatives (e.g., "You spent $42 on GPT-4o — GPT-4o-mini would've cost $1.68")
- **🔌 Drop-in middleware** — Wraps OpenAI and Anthropic clients with zero code changes
- **🖥️ Web dashboard** — FastAPI-powered dark-themed dashboard with live updates
- **👥 Multi-team support** — Isolate spend by team, project, or API key
- **💻 CLI** — Full command-line interface for scripting and CI/CD

## Quick Start

```bash
pip install ai-cost-guard
```

### Track usage via middleware

```python
from openai import OpenAI
from aicostguard.middleware import OpenAIInterceptor

client = OpenAI()
tracked = OpenAIInterceptor(client, team_id="engineering")

# Use normally — usage is tracked automatically
response = tracked.chat_completions_create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Track usage manually

```python
from aicostguard.middleware import CostGuardMiddleware

guard = CostGuardMiddleware(team_id="my-team")
cost = guard.track("openai", "gpt-4o", input_tokens=1000, output_tokens=500)
print(f"Cost: ${cost:.4f}")
```

### CLI

```bash
# Estimate cost before making a call
ai-cost-guard estimate openai gpt-4o 10000 5000

# Record usage
ai-cost-guard track openai gpt-4o 10000 5000 --team engineering

# Check spend
ai-cost-guard spend --period daily --team engineering

# Set a budget
ai-cost-guard budget set --limit 50.00 --period daily --provider openai --alert-pct 80

# Check budgets
ai-cost-guard budget check

# View waste report
ai-cost-guard waste --period monthly

# List all known prices
ai-cost-guard prices
```

### Dashboard

```bash
uvicorn aicostguard.dashboard:app --port 8080
```

Open http://localhost:8080 for the live dashboard.

## Supported Providers & Models

### OpenAI
- GPT-4o, GPT-4o-mini, GPT-4 Turbo, GPT-4, GPT-3.5 Turbo
- o1, o1-mini, o3-mini

### Anthropic
- Claude Sonnet 4, Claude Opus 4, Claude Haiku 4
- Claude 3.5 Sonnet, Claude 3.5 Haiku, Claude 3 Opus

### Google
- Gemini 2.5 Pro, Gemini 2.5 Flash, Gemini 2.0 Flash
- Gemini 1.5 Pro, Gemini 1.5 Flash

## Architecture

```
aicostguard/
├── __init__.py        # Package init
├── pricing.py         # Model pricing data + cost estimation
├── tracker.py         # SQLite storage, budgets, alerts, waste detection
├── middleware.py       # OpenAI/Anthropic interceptors + manual tracker
├── cli.py             # Full CLI (estimate, track, spend, budget, alerts, waste)
└── dashboard.py       # FastAPI web dashboard
```

## Configuration

All configuration via CLI flags or API parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--db` | `aicostguard.db` | SQLite database path |
| `--team` | `default` | Team identifier |
| `--period` | `daily` | Budget period (daily/weekly/monthly) |
| `--alert-pct` | `80` | Alert threshold (% of budget) |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard (HTML) |
| GET | `/api/spend` | Total spend (query: period, provider, team) |
| GET | `/api/spend/by-model` | Spend breakdown by model |
| POST | `/api/track` | Record a usage event |
| GET | `/api/alerts` | Get active alerts |
| POST | `/api/budget` | Set a budget |
| POST | `/api/budget/check` | Check all budgets |
| GET | `/api/waste` | Waste report |
| GET | `/api/prices` | All known prices |

## Development

```bash
git clone https://github.com/Jsardhara/forge-projects
cd 2026-06-02-ai-cost-guard
uv venv && uv pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
