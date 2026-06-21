# Project Justification: ModelRouter — GLM-5.2 OpenAI-Compatible Gateway

## Problem
GLM-5.2 (MIT-licensed, open weights) scores 91 vs GPT-5.5's 87 on BenchLM aggregate, with 62.1 SWE-bench Pro vs 58.6, at $1.40/$4.40 per M tokens vs $5/$30 — a 70%+ cost reduction with better quality. But switching existing OpenAI-based applications to GLM-5.2 requires code changes: different base_url, different model names, different error handling. Teams need a drop-in proxy that accepts OpenAI-format requests and routes them to GLM-5.2 (or any OpenAI-compatible endpoint) with automatic fallback, health checks, and cost tracking.

## Who Uses This
- Engineering teams running AI-powered features on OpenAI that want to reduce costs by 70%+ without code changes
- Startups building on OpenAI that need a migration path to open models
- Enterprises evaluating GLM-5.2 as a GPT replacement but needing zero-downtime migration
- Developers who want model-agnostic infrastructure that isn't locked into OpenRouter/Helicone SaaS

## Why Existing Solutions Are Inadequate
- **OpenRouter**: SaaS-only, adds latency, doesn't optimize for GLM-5.2 specifically, costs extra on top of model pricing
- **Helicone**: Observability-focused, not a routing gateway; fallback is beta
- **LiteLLM**: Feature-heavy but complex to self-host; no GLM-5.2-specific optimizations
- **XiDao router**: Provider-specific to XiDao, not general-purpose
- **Direct base_url swap**: No fallback, no health checks, no cost tracking, no model mapping

## Success Criteria
- Drop-in OpenAI SDK compatibility (change only base_url)
- Automatic fallback from GLM-5.2 to backup provider on failure
- Health check endpoint for monitoring
- Cost tracking per request (input/output tokens × provider rates)
- Model name mapping (e.g., "gpt-4o" → "z-ai/glm-5.2")
- Zero external dependencies for core routing logic (stdlib only)
