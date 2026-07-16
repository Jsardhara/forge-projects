# tokenaudit

**Coding-agent token-cost profiler & efficiency auditor.**

tokenaudit ingests a finished coding-agent session transcript (Claude Code JSONL or
generic JSONL) and explains *where the tokens went and why* -- then tells you what to
change to cut the bill. It is the offline **diagnostic** layer that live
spend-trackers (proxies, routers, guardrails) don't provide.

## Why
A single agent session can spend tens of thousands of input tokens loading context
before it does any work, re-read the same files every turn, and re-feed identical
large tool output back into the model. Lens flagged this directly: a benchmark showed
one agent sending ~33k tokens before reading the prompt while another sent ~7k.

## Install
```bash
pip install .
```
Zero runtime dependencies (Python standard library only).

## Usage
```bash
# Profile one transcript
tokenaudit profile session.jsonl
tokenaudit profile session.jsonl --format json

# Compare two agents / configs head-to-head (the 33k-vs-7k question)
tokenaudit compare claude_session.jsonl opencode_session.jsonl

# Batch-profile every .jsonl in a directory
tokenaudit report ./sessions/

# Override model prices (USD per 1M tokens): {"model": [in, out], ...}
tokenaudit profile session.jsonl --prices prices.json
```

## What it finds
| Phase | Meaning |
| --- | --- |
| Pre-read (before 1st tool) | Input tokens loaded as setup/context before the agent works |
| Tool results | Input tokens from tool output returned to the model |
| Other input | Follow-up instructions, summaries |
| Generation | Output tokens produced |

### Waste detectors
- **PRE_READ_OVERHEAD** -- too much context before the first tool call.
- **REDUNDANT_READS** -- the same file read more than once.
- **TELEMETRY_OVERHEAD** -- the same large tool output re-fed every turn.
- **CONTEXT_BLOAT** -- context grew far faster than output (monotonic accumulation).

Each finding carries a severity and an *estimated* recoverable cost (conservative:
at most half of the flagged volume). Recommendations are prioritized with a rough
potential-savings share.

## Pricing note
The built-in price table is **illustrative** public list pricing (USD/1M tokens),
approximate as of 2026-06. Override with `--prices` and verify against provider
pricing pages before making billing decisions. Prices change.

## Tests
```bash
pip install pytest
pytest tests/ -v
```
