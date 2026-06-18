# Agent Royale 🏟️

**Competitive AI Agent Benchmarking Platform**

Put your AI agents head-to-head in structured competitions. Score, rank, and crown the best.

## What It Is

Agent Royale is a Python framework for running competitive benchmarks between AI agents. Inspired by [OpenRouter's Royale experiment](https://openrouter.ai/blog/insights/royale-last-agent-standing/) (HN #15, 245pts), it gives you:

- **Arena matches** — pit 2+ agents against each other in debate, coding, or trivia challenges
- **Tournament brackets** — single-elimination tournaments with automatic advancement
- **Scoring engine** — heuristic scoring across game modes (plug in your own LLM judge)
- **Leaderboard** — persistent rankings by score and win rate
- **CLI** — register agents, run matches, view standings from the terminal

## Quickstart

```bash
pip install -e ".[dev]"
agent-royale register "GPT-4o" "openai/gpt-4o"
agent-royale register "Claude Opus" "anthropic/claude-opus-4"
agent-royale leaderboard
```

## Architecture

```
agent_royale/
├── __init__.py    # IdentityRegistry, Agent, Match models
├── arena.py       # Arena + ScoringEngine
├── bracket.py     # Tournament bracket management
└── cli.py         # CLI interface
```

## Game Modes

| Mode | Scoring Criteria |
|------|-----------------|
| **Debate** | Length, structure, reasoning keywords, persuasiveness |
| **Coding** | Code presence, formatting, tests, comments |
| **Trivia** | Exact match, partial credit, confidence markers |

## Roadmap

- [ ] LLM-judge scoring (replace heuristics with actual LLM evaluation)
- [ ] REST API (FastAPI server)
- [ ] WebSocket streaming for live match updates
- [ ] OpenRouter integration for real agent-vs-agent battles
- [ ] Web dashboard (Next.js + shadcn/ui)
- [ ] Team subscriptions & billing

## License

MIT
