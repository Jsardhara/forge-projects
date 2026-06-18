# Project Justification: Agent Battle Royale

## Problem
AI agents are proliferating but there's no standardized way to benchmark them against each other. OpenRouter's "Royale" experiment (HN #15, 245pts) proved massive demand: pitting LLMs against each other in competitive scenarios generated huge engagement. Companies building AI agents have no tool to test agent quality, regression-test after model changes, or prove their agent is better than competitors.

## User
- AI startups wanting to benchmark their agents against competitors
- Enterprise AI teams needing regression testing after model/provider changes
- Model providers (OpenAI, Anthropic, etc.) wanting to showcase agent capabilities
- Developer tools companies building agent evaluation pipelines

## Why Existing Solutions Are Inadequate
- **OpenRouter Royale**: One-off blog experiment, no API, no repeatable framework
- **LM Eval Harness**: Academic, text-only, no competitive/multi-agent scenarios
- **AgentBench**: Static benchmarks, no real-time competitive arena
- **Custom scripts**: Every team rebuilds from scratch, no shared scoring/leaderboard

## Success Metrics
- Functional arena engine supporting 2+ concurrent LLM players
- Scoring system that ranks agents by task completion, quality, and efficiency
- Leaderboard API that persists results across runs
- At least 3 arena game modes (debate, coding challenge, trivia)
- 90%+ test coverage
