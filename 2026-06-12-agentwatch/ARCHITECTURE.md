# AgentWatch — Architecture

## System Overview

AgentWatch is a dual-purpose monitoring platform for AI agents:

1. **Cost Monitor**: Tracks API spending per-agent with configurable budgets, hard caps, and alerts
2. **Guardrail Probe**: Detects invisible model guardrails by sending standardized test prompts and measuring response drift

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  AI Agents  │────▶│  AgentWatch  │────▶│ Slack/Discord/  │
│  (monitored)│     │  API Server  │     │ Webhook Alerts  │
└─────────────┘     └──────┬───────┘     └─────────────────┘
                           │
                    ┌──────┴───────┐
                    │   SQLite DB  │
                    │ (spend,     │
                    │  probes,    │
                    │  alerts)    │
                    └──────────────┘
```

## Components

### `db.py` — Storage Layer
- Single SQLite database with WAL mode
- Tables: agents, spend_records, budgets, guardrail_probes, guardrail_results, alerts
- All CRUD operations return dicts

### `cost.py` — Cost Tracking
- `estimate_cost()`: Token-to-USD conversion for 6+ models (GPT-4o, Claude Sonnet/Haiku, Gemini Pro/Flash)
- `check_budget()`: Compares spend against daily/monthly limits, auto-creates alerts
- `SpendReport`: Dataclass with spend percentages and alert states

### `guardrail.py` — Guardrail Detection
- `run_probe()`: Sends prompts, checks keyword presence, calculates drift score (0.0–1.0)
- `get_drift_trend()`: Returns historical drift for trend analysis
- Supports pluggable `call_model_fn` — defaults to simulation, pass real API caller in production
- Drift > 0.5 = probe FAILS; 3-check rolling average > 0.3 = drift alert

### `api.py` — FastAPI REST API
- 14 endpoints: agent CRUD, spend recording, budget management, guardrail probes, alerts, cost estimation
- Uses `@asynccontextmanager` lifespan (FastAPI 0.115+ pattern, no deprecated `on_event`)
- Pydantic request models for all POST endpoints

### `cli.py` — Command Line
- `agentwatch init`: Creates default agent + probe
- `agentwatch check`: Runs all cost + guardrail checks, prints summary
- `agentwatch serve`: Starts uvicorn server
- `agentwatch estimate`: Cost estimation from tokens

## Data Model

```
agents (agent_id PK, name, provider, created_at)
  └──▶ spend_records (id, agent_id FK, tokens_in, tokens_out, cost_usd, recorded_at)
  └──▶ budgets (agent_id FK PK, daily_limit_usd, monthly_limit_usd, alert_threshold_pct)

guardrail_probes (probe_id PK, name, provider, model, prompt, expected_keywords, interval_seconds, created_at)
  └──▶ guardrail_results (id, probe_id FK, response_text, keywords_found, keywords_missing, drift_score, passed, checked_at)

alerts (id, alert_type, agent_id, probe_id, message, severity, created_at, acknowledged)
```

## Production Deployment

For production use, pass a real model caller to `run_probe()`:

```python
import openai

def call_openai(prompt: str) -> str:
    resp = openai.chat.completions.create(
        model="gato",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content

result = run_conn, "probe-1", call_model_fn=call_openai)
```
