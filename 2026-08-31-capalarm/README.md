# capalarm

**Subscription AI plan-cap compliance & headroom forecaster.**

Given your actual AI-subscription usage records and the token/rate caps of your
capped plan, `capalarm` tells you:

- **Headroom:** what % of your monthly token hard-cap you've consumed
- **Soft/hard-cap alerts:** WARN once you cross your soft cap, CRIT when you hit the hard cap
- **Rate-tier checks:** your peak tokens-per-minute vs the plan's rate limit
- **Days-to-breach forecast:** linear burn-rate projection to plan exhaustion

Spend-trackers (`ai-cost-guard`, `costrecon`, `tokenaudit`) answer "how much did I
spend". `capalarm` answers the question they don't: *"what % of my plan cap is
gone and when will it break?"*

## Install

```bash
pip install --no-cache-dir .
```

## Usage

Feed usage as CSV or JSON (default: stdin, JSON) and get a verdict + exit code:

```bash
# JSON records
cat usage.json | capalarm

# CSV file, force a plan
capalarm usage.csv --format csv --plan anthropic-claude-max

# Focus on one provider, machine-readable output
capalarm usage.json --provider anthropic --json
```

### Input format

**JSON** — list of records, or `{"records": [...]}`:

```json
[
  {"provider": "anthropic", "timestamp": "2026-08-31T12:00:00Z", "tokens": 1500000},
  {"provider": "anthropic", "timestamp": "2026-08-31T12:05:00Z", "tokens": 50000}
]
```

**CSV** — columns `provider,timestamp,tokens`:

```csv
provider,timestamp,tokens
anthropic,2026-08-31T12:00:00Z,1500000
anthropic,2026-08-31T12:05:00Z,50000
```

Timestamps are ISO-8601; naive values are treated as UTC.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | All checks PASS |
| 1 | At least one WARN (soft cap / imminent breach / rate tier) |
| 2 | At least one CRIT (hard cap hit) OR parse/plan error |

Use in CI/gates: fail a pipeline when a plan is about to be exhausted.

## Plans

Curated default plans (editable presets — bring your own config for precision):

| id | provider | hard cap | soft cap | rate tier |
|----|------|----------|----------|-----------|
| anthropic-claude-max | anthropic | 2.0M | 1.6M | 60k t/m |
| anthropic-claude-max-premium | anthropic | 8.0M | 6.4M | 60k t/m |
| openai-chatgpt-plus | openai | 1.2M | 0.96M | 30k t/m |
| google-gemini-ultra | google | 2.5M | 2.0M | 40k t/m |

Provider auto-resolution picks the first matching plan; use `--plan <id>` to force.

## Development

```bash
pip install pytest
pytest tests/ -v
```

Zero runtime dependencies — pure standard library.

## License

MIT