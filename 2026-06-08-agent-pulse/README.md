# AgentPulse — Multi-Agent Activity Dashboard

A real-time dashboard for monitoring the Jarmes multi-agent system. Shows agent activity, build history, sentinel health, bus messages, and system costs in a single view.

## Problem

The Jarmes multi-agent system runs 7+ specialist agents producing logs across dozens of JSONL files. There's no unified view — you have to ask Jarmes, check Discord channels, or manually inspect log files. AgentPulse solves this with a single dashboard.

## Quick Start

```bash
cd 2026-06-08-agent-pulse
env -u PYTHONHOME /c/Users/jyot2/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pip install -e ".[dev]"
env -u PYTHONHOME /c/Users/jyot2/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8765
```

Then open http://localhost:8765 in your browser.

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `AGENTPULSE_STATE_DIR` | `C:\Users\jyot2\jarvis\state` | Path to JSONL state files |
| `AGENTPULSE_BUS_DIR` | `~\AppData\Local\hermes\state\bus` | Path to bus directory |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Dashboard HTML |
| `GET /api/all` | All data in one call |
| `GET /api/stats` | Aggregated statistics |
| `GET /api/builds?limit=20` | Build history |
| `GET /api/agents?limit=50` | Agent activity feed |
| `GET /api/health?limit=10` | Sentinel health checks |
| `GET /api/costs?limit=100` | Cost log entries |
| `GET /api/bus?limit=20` | Bus messages |

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for system overview and design decisions.

## Tests

```bash
env -u PYTHONHOME /c/Users/jyot2/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest tests/ -v
```

26 tests covering readers, models, and API endpoints.

## Known Limitations

- Read-only: never writes to state files
- Polls every 30s (no WebSocket)
- Localhost only (no auth)
- Reads from local filesystem only
