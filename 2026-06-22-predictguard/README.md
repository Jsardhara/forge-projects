# PredictGuard — Prediction Market Compliance Platform

Compliance monitoring, audit trails, and risk scoring for prediction markets.

## Why

Prediction markets are under regulatory fire:
- Polymarket paid creators to post deceptive videos about fake bets (June 2026)
- CFTC actively policing insider trading and manipulation
- 8+ states issued cease-and-desist orders
- Multiple Congressional bills in play (PREDICT Act, Prediction Markets Are Gambling Act)

Compliance teams have **zero tooling** to monitor, audit, and report on prediction market activity. PredictGuard fills that gap.

## Features

- **State-by-state regulatory tracker** — All 50 US states + key international jurisdictions
- **Trade ingestion** — Import trades from Kalshi, Polymarket, Crypto.com (CSV/JSON)
- **Risk scoring engine** — Detect wash trading, coordinated manipulation, insider patterns
- **Audit trail export** — Regulator-ready CSV/JSON reports
- **Compliance scoring** — Automated compliance score based on regulatory requirements
- **Stdlib only** — Zero external dependencies for core logic

## Quick Start

```bash
pip install -e ".[dev]"
predictguard status                    # Show regulatory status summary
predictguard ingest trades.csv         # Ingest trade data
predictguard risk --threshold 0.7      # Run risk analysis
predictguard report --format csv       # Generate compliance report
predictguard audit --output audit.json # Export audit trail
```

## Test

```bash
pytest tests/ -v
```

## Architecture

```
src/predictguard/
  __init__.py      — Package exports
  __main__.py      — python -m predictguard entry point
  cli.py           — CLI commands (typer-free, argparse-based)
  models.py        — Trade, Market, ComplianceReport dataclasses
  regulatory.py    — State-by-state regulatory status database
  risk.py          — Risk scoring engine
  audit.py         — Audit trail generation
  report.py        — Compliance report generation
```
