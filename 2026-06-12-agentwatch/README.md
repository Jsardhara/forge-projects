# AgentWatch — AI Agent Cost & Guardrail Monitoring

> Datadog for AI agent behavior + model transparency

Two massive problems converged in June 2026:
1. **AI agents bankrupt operators** — An agent ran up a $6,531 AWS bill with zero visibility
2. **Invisible model guardrails** — Anthropic silently throttled competing AI development

AgentWatch solves both: real-time cost monitoring with hard spending caps, plus guardrail detection that probes models and flags when outputs are being silently modified.

## Features

- **Cost Monitor**: Track API spending per-agent with configurable budgets and hard caps
- **Guardrail Probe**: Send standardized test prompts to models and detect response drift over time
- **Alert Engine**: Slack/Discord/webhook alerts for spending anomalies and guardrail triggers
- **REST API**: FastAPI backend with per-agent dashboards
- **CLI**: `agentwatch check` for quick status from the terminal

## Quick Start

```bash
pip install ".[dev]"
agentwatch init                    # create config
agentwatch check                   # run cost + guardrail checks
agentwatch serve --port 8080       # start API server
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/agents` | List all monitored agents |
| POST | `/agents` | Register a new agent |
| GET | `/agents/{id}/spend` | Get spending data for an agent |
| POST | `/agents/{id}/budget` | Set budget cap for an agent |
| GET | `/guardrails` | List all guardrail probes |
| POST | `/guardrails` | Create a new guardrail probe |
| POST | `/guardrails/{id}/check` | Run a guardrail check |
| GET | `/alerts` | List recent alerts |

## Config

`.env`:
```
AGENTWATCH_DB_PATH=agentwatch.db
AGENTWATCH_SLACK_WEBHOOK_URL=https://hooks.slack.com/...
AGENTWATCH_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Tests

```bash
pytest tests/ -v --cov=agentwatch
```

## License

MIT
