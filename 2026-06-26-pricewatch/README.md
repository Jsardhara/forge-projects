# PriceWatch — LLM Provider Price Intelligence Monitor

PriceWatch monitors LLM API pricing across OpenAI, Anthropic, Google, and Mistral. It detects price changes, tracks price wars, and alerts when models become cheaper or more expensive — giving teams the data to route to the most cost-effective model before the competition does.

## Why This Exists

LLM pricing is volatile. OpenAI dropped GPT-4o pricing 50% in 2024, Anthropic introduced Claude Haiku at a fraction of Sonnet's cost, and Google slashed Gemini prices to compete. Teams that don't track these changes overpay by 2-10x. Existing tools (llm-pricing, openai-pricing) only snapshot current prices — they don't track changes, detect trends, or alert on price drops. PriceWatch fills that gap.

## Features

- **Multi-provider tracking**: OpenAI, Anthropic, Google Gemini, Mistral
- **Change detection**: Flags price increases and decreases with magnitude
- **Trend analysis**: 7-day and 30-day price trend per model
- **Price war detection**: Identifies when multiple providers drop prices for equivalent models
- **Ranking engine**: Ranks models by cost-efficiency (price per 1M tokens) for each capability tier
- **Alert generation**: Structured alerts for price drops >10%, price wars, and new model listings
- **CLI interface**: `pricewatch scan`, `pricewatch compare`, `pricewatch alerts`, `pricewatch trends`
- **JSON output**: Machine-readable for integration with model routers and cost optimizers

## Install

```bash
pip install .
```

## Usage

```bash
# Scan all providers for current prices
pricewatch scan

# Compare models across providers
pricewatch compare --tier coding

# Show recent price alerts
pricewatch alerts --since 7d

# Show price trends
pricewatch trends --model gpt-4o
```

## Architecture

PriceWatch uses a provider-agnostic model: each provider returns a list of `ModelPricing` entries. A `PriceStore` persists snapshots over time (SQLite). The `ChangeDetector` compares snapshots to find deltas. The `AlertEngine` generates alerts from deltas. The `RankingEngine` sorts models by cost-efficiency.

## Sources

- [Lens Intel — AI Memory Cost Crisis](C:/Users/jyot2/jarvis/state/lens-daily-intel.md)
- [Reuters — Apple raises prices on MacBooks/iPads as memory costs skyrocket](https://www.reuters.com/world/asia-pacific/apple-raises-prices-macbooks-ipads-memory-costs-skyrocket-2026-06-25/)
- [TechCrunch — Databricks former AI chief thinks he can cut AI's power bill by 1000x](https://techcrunch.com/2026/06/25/databricks-former-ai-chief-thinks-he-can-cut-ais-power-bill-by-1000x/)

## License

MIT
