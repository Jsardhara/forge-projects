# AgentOS — AI Agent Orchestration & Governance Platform

**The "Vercel for AI agent operations."**

AgentOS provides policy enforcement, cost controls, and audit trails for teams running multiple AI agents (Claude Code, Codex, custom). Think Kubernetes-style governance for the agent economy.

## Why Now

- Databricks just open-sourced Omnigent (Apache 2.0) — proving the multi-agent orchestration market
- 82% of organizations expect to fully integrate AI agents (Boomi survey)
- Zero user-friendly governance tools exist today
- AI agent cost explosions are real (Uber capped at $1,500/mo after blowing budget)
- Fable 5 safety crisis proved agent behavior is unpredictable

## Features

1. **Policy Engine** — Enforce spending caps, tool access controls, and human-in-the-loop approval gates
2. **Cost Dashboard** — Real-time token usage tracking per agent, per project, per team member
3. **Audit Logging** — Every agent action recorded with timestamp, input, output, cost, and policy decisions
4. **Agent Registry** — Register and manage multiple AI agents with different capabilities
5. **Compliance Reports** — Exportable audit trails for SOC2/GDPR/regulatory audits

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the server
uvicorn agentos.main:app --reload --port 8000

# Run tests
pytest tests/ -v
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard (HTML) |
| GET | `/api/agents` | List all agents |
| POST | `/api/agents` | Register a new agent |
| GET | `/api/agents/{id}` | Get agent details |
| GET | `/api/policies` | List all policies |
| POST | `/api/policies` | Create a policy |
| POST | `/api/policies/{id}/check` | Check a request against policy |
| GET | `/api/audit` | List audit log entries |
| POST | `/api/audit` | Record an audit event |
| GET | `/api/costs` | Get cost summary |
| GET | `/api/costs/{agent_id}` | Get cost for specific agent |
| GET | `/api/health` | Health check |

## Tech Stack

- **Backend:** Python 3.11+ / FastAPI / SQLAlchemy / SQLite
- **Frontend:** Server-rendered HTML + vanilla JS (Jinja2 templates)
- **Testing:** pytest + pytest-asyncio

## License

MIT
