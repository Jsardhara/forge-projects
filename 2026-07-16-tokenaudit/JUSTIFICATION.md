# Project Justification: tokenaudit

## Problem
Coding agents (Claude Code, OpenCode, Codex, Cursor) now burn real token budgets,
and developers have almost no visibility into *where* the tokens go. The issue is
structural, not volumetric: a single session can spend tens of thousands of input
tokens loading context before it does any work, re-read the same files every turn,
and re-feed identical large tool output back into the model. Lens flagged this
directly: a widely-read benchmark showed Claude Code sending ~33k tokens before
reading the prompt while OpenCode sent ~7k (590 pts, HN Best; systima.ai telemetry
write-up). Developers want to cut that bill but cannot see the breakdown.

## User
A developer who runs coding agents and pays per token (API or subscription metered
by usage). Also directly useful to us: this tool can profile the Jarmes system's own
agent runs, making it *self-improving* (preference tier 1).

## Why existing solutions are inadequate
The forge-projects repo already has four tools in the "AI cost" category, but every
one is a **live/runtime** tool:
- `ai-cost-guard` (06-02) -- spend guardrails / budget enforcement at request time.
- `ai-token-proxy` (06-04) -- a middleware proxy that counts tokens live.
- `model-router` (06-21) -- selects which model to call + aggregates cost live.
- `pricewatch` (06-26) -- monitors cross-provider *price* changes.

None of them answer the diagnostic question: "In this session transcript, which
phases (pre-read, tool results, redundant reads, telemetry) consumed my tokens, and
what should I change?" tokenaudit is the **offline profiler** layer -- it ingests a
finished session transcript and explains the *shape* of the spend. That is a distinct
layer (post-hoc diagnosis vs live tracking/routing/pricing), so this is a reframe,
not a duplicate. (Documented per the daily-build-dedup workflow.)

## How we'll know it's successful
- Parses real Claude Code JSONL transcripts and generic JSONL.
- Produces a phase breakdown (pre-read / tool-result / other / generation).
- Detects the four waste classes with severity + estimated recoverable cost.
- Emits prioritized, conservative recommendations.
- CLI works end-to-end (`profile`, `compare`, `report`) and tests are green.
- Reused later to audit Jarmes/Forge agent runs (self-improving loop).

## Build type
Greenfield, zero external dependencies (stdlib only), hatchling `src/` layout.
