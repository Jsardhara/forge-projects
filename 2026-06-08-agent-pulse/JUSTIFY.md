# Project Justification: AgentPulse

## Problem
The Jarmes multi-agent system runs 7+ specialist agents (Tempo, Scholar, Lens, Forge, Atlas, Sentinel, Jarmes) plus cron jobs, all producing logs and state across dozens of JSONL files in `C:\Users\jyot2\jarvis/state/`. When the operator wants to know "what's happening right now," they have to either ask Jarmes (which requires a conversation), check Discord channels (fragmented), or manually inspect log files (tedious). There is no single, always-on, visual dashboard that shows the system's pulse.

## Existing Solutions
- **Discord channels**: Each agent posts to its own channel (#tempo, #forge, #sentinel, etc.). No unified view. Requires scrolling through multiple channels.
- **Jarmes conversation**: Works but is pull-based — you have to ask. No ambient awareness.
- **Log files**: Raw JSONL in `/state/`. Not human-readable at a glance.
- **No existing tool**: Nothing aggregates agent activity, build history, sentinel health, and bus messages into one dashboard.

## Proposed Solution
**AgentPulse** — a Python/FastAPI + vanilla HTML/JS dashboard that:
1. Reads all JSONL state files from `/jarvis/state/`
2. Serves a REST API with aggregated metrics
3. Renders a real-time (30s refresh) dashboard showing:
   - **Agent Activity Feed**: Recent actions across all agents (from agent_log.jsonl)
   - **Build History**: Forge daily builds with status, cost, duration (from daily_projects.jsonl)
   - **Sentinel Health**: Job status and health check results (from sentinel_health.jsonl)
   - **System Costs**: Daily/weekly API spend (from cost_log.jsonl)
   - **Bus Messages**: Recent inter-agent messages (from bus inbox)
   - **Quick Stats**: Total builds, success rate, active agents, uptime

## Impact Criteria
- Operator can see system status in <5 seconds without asking Jarmes
- Dashboard loads in <2s on localhost
- All data is read-only (no mutations to system state)
- Deployable as a local service (no external dependencies)

## Why now
- The system has been running for 6 weeks with growing complexity
- More agents and cron jobs are being added over time
- WWDC 2026 is this week (per Lens intel) — Apple ecosystem changes may affect the system
- The forge-scaffold project (built yesterday) makes future builds faster, but monitoring those builds still requires manual log inspection
