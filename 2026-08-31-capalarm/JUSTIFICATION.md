# Project Justification: capalarm

## What real problem does this solve?
Capped-AI-plan users (Claude Max, ChatGPT Plus/Pro, Gemini Ultra, any usage-capped
subscription) silently wander toward their monthly token hard-cap. Providers force
through *soft* caps with degraded throughput or cut you off at *hard* caps mid-
workflow — alienating-building and interrupting agent runs. Spend-trackers
(`ai-cost-guard`, `costrecon`, `tokenaudit`) answer "how much *money/spend* did I
burn"; none answer *"what % of my plan's token/rate cap have I consumed and when
will I breach it?"* Plan caps, rate-limit tiers, and days-to-breach forecasting are
a distinct layer no existing build covers.

## Who is the user?
Engineers running heavy agent/LLM workloads on capped subscription tiers who need a
proactive "you will breach your cap in N days" alert before the provider enforces it.

## Why are existing solutions inadequate?
- `ai-cost-guard` / `costrecon`: dollar-cost spend tracking, not token-cap headroom.
- `tokenaudit`: spend-side complement; no plan-tier cap/rate compliance.
- `pricewatch`: price-change intelligence, unrelated to plan usage caps.
None consume your actual usage records and report cap-consumption % + a
time-to-cap forecast against your specific provider plan.

## How do we know it's successful?
A titled CLI that, given a usage CSV/JSON, prints per-provider `78% hard-cap ·
soft-cap WARN · rate 640t/m <= 1,000t/m · on pace to breach in 4.2d`, exits 0/1/2
for CI embedding, and ships with unit tests proving the aggregation/forecast math.