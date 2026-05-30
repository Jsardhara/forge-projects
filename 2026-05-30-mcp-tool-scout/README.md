# MCP Tool Scout

Discover, score, and search MCP (Model Context Protocol) servers for AI agents.

Think "npm search but for MCP servers" — a developer-facing API and CLI that aggregates MCP server repos from GitHub, scores them by quality signals, and serves a searchable catalog.

## Why This Exists

The MCP ecosystem is exploding. There are hundreds of MCP servers on GitHub, but no good way to:
- **Discover** which ones exist for your use case
- **Evaluate** quality beyond star count
- **Compare** servers head-to-head
- **Integrate** programmatically via API

MCP Tool Scout solves this with a scoring engine and search API.

## Quick Start

```bash
# Install dependencies
cd 2026-05-30-mcp-tool-scout
uv pip install -e ".[dev]"

# Run CLI with seed data (no GitHub token needed)
python cli_collect.py collect

# Start the API server
python cli_collect.py serve --port 8765

# Score a specific server
python cli_collect.py score github
```

### With GitHub Token (live data)

```bash
export GITHUB_TOKEN=ghp_xxxx
python cli_collect.py collect --token ghp_xxxx
python cli_collect.py serve
```

## API

| Endpoint | Description |
|----------|-------------|
| `GET /` | Service info |
| `GET /health` | Health check |
| `GET /servers` | List/search servers (`?q=github&min_score=50&sort=stars`) |
| `GET /servers/top` | Top N servers (`?limit=10`) |
| `GET /servers/{id}` | Server details |
| `GET /servers/{id}/score` | Detailed scoring breakdown |
| `POST /collect` | Trigger GitHub refresh (requires token) |

### Example

```bash
# Search for database-related MCP servers
curl "http://127.0.0.1:8765/servers?q=database&sort=stars"

# Get a server's score breakdown
curl "http://127.0.0.1:8765/servers/{id}/score"
```

## Scoring Engine

Servers are scored 0-100 on four weighted dimensions:

| Dimension | Weight | Signals |
|-----------|--------|---------|
| Popularity | 30% | Stars, forks, watchers (log scale) |
| Activity | 30% | Last push recency, issue ratio |
| Documentation | 25% | README length, topics count |
| Freshness | 15% | Age sweet spot (1-12 months) |

Recommendations are generated automatically based on score profile.

## Project Structure

```
2026-05-30-mcp-tool-scout/
  mcp_tool_scout/
    __init__.py      # Domain models, scoring engine, store, GitHub collector
    app.py           # FastAPI application
  cli_collect.py     # Click CLI (collect, serve, score commands)
  tests/
    __init__.py      # Comprehensive test suite (40+ tests)
  README.md
  MONETIZATION.md
  pyproject.toml
```
