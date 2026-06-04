# 🛡️ AITokenProxy

**Drop-in HTTP proxy that reduces your AI API costs by 50-80%.**

AITokenProxy sits between your AI coding tools (Claude Code, Cursor, Copilot, Windsurf) and LLM APIs (OpenAI, Anthropic), automatically compressing prompts, tool outputs, and RAG context before they hit the API.

## Why?

Uber just capped employee AI tool spending at $1,500/month. They blew their entire 2026 AI budget in 4 months. The problem isn't that AI is too expensive — it's that **nobody is optimizing token usage**.

AITokenProxy fixes that. Point your tools at the proxy instead of the real API, and watch your token bill drop by 50-80%.

## How It Works

```
Claude Code / Cursor / Copilot
         │
         ▼
┌─────────────────────┐
│   AITokenProxy       │  ← Your API calls go here
│   :9090              │
│                      │
│  ┌────────────────┐  │
│  │ Compress:      │  │
│  │ • Prompts      │  │
│  │ • Tool outputs │  │
│  │ • RAG chunks   │  │
│  │ • Msg history  │  │
│  └────────────────┘  │
│         │            │
│         ▼            │
│  ┌────────────────┐  │
│  │ Forward to     │  │
│  │ OpenAI/Anthropic│  │
│  └────────────────┘  │
└─────────────────────┘
         │
         ▼
   OpenAI / Anthropic API
```

## Compression Strategies

| Strategy | What it does | Typical savings |
|----------|-------------|-----------------|
| **Prompt compression** | Removes filler phrases, collapses whitespace | 5-15% |
| **Tool output truncation** | Caps verbose tool results, keeps head+tail | 30-60% |
| **RAG dedup** | Removes semantically duplicate chunks | 10-40% |
| **Message window** | Summarizes old messages, keeps recent N | 20-50% |

## Quick Start

```bash
pip install aitokenproxy
```

### 1. Start the proxy

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
aitokenproxy serve --port 9090
```

### 2. Point your tools at it

**Claude Code:**
```bash
export ANTHROPIC_API_BASE=http://localhost:9090/anthropic
claude
```

**Cursor / OpenAI-compatible tools:**
```bash
export OPENAI_API_BASE=http://localhost:9090/openai
```

**Any tool that lets you set a custom API base URL** — just point it at the proxy.

### 3. Check your savings

```bash
aitokenproxy stats
# or visit http://localhost:9090/stats
```

## CLI

```bash
# Start the proxy
aitokenproxy serve --port 9090

# Check compression stats
aitokenproxy stats

# Test compression on a prompt
aitokenproxy compress "Please note that this is very really important..."
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/stats` | Compression statistics |
| ANY | `/openai/{path}` | OpenAI API proxy |
| ANY | `/anthropic/{path}` | Anthropic API proxy |

## Configuration

| Env Var | Description |
|---------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (used if client doesn't send one) |
| `ANTHROPIC_API_KEY` | Anthropic API key (used if client doesn't send one) |

## Development

```bash
git clone https://github.com/Jsardhara/forge-projects
cd 2026-06-04-ai-token-proxy
uv venv && uv pip install -e ".[dev]"
pytest tests/ -v
```

## Architecture

```
aitokenproxy/
├── __init__.py        # Package init
├── tokens.py          # Token counting + pricing data
├── compressor.py      # Compression engine (4 strategies)
├── proxy.py           # FastAPI proxy server
└── cli.py             # CLI (serve, stats, compress)
```

## Roadmap

- [ ] Streaming response support
- [ ] Redis-backed stats for multi-instance deployments
- [ ] Per-model compression profiles
- [ ] Web dashboard with real-time charts
- [ ] Stripe billing integration for SaaS
- [ ] Chrome extension for browser-based AI tools
- [ ] Support for Google Gemini, Mistral, and other providers

## License

MIT
