# Project Justification: PredictGuard

## Problem
Prediction markets are under regulatory fire. On June 21, 2026, TechCrunch reported that Polymarket paid creators to post deceptive videos about fake bets on copycat sites. The CFTC is actively policing insider trading and manipulation. At least 8+ states have issued cease-and-desist orders against prediction market operators. Multiple Congressional bills (PREDICT Act, Prediction Markets Are Gambling Act) are in play. Yet compliance teams at financial firms, trading desks, and prediction market operators have **zero tooling** to monitor, audit, and report on prediction market activity.

## Who Uses This
- **Compliance officers** at hedge funds and proprietary trading firms whose employees trade on Kalshi/Polymarket
- **Prediction market operators** (Kalshi, Polymarket, Crypto.com) needing audit trails for CFTC examinations
- **Legal teams** tracking regulatory changes across 50 states and international jurisdictions

## Why Existing Solutions Are Inadequate
- Hadrius (hadrius.com) just launched prediction market monitoring but it's a closed enterprise product — no self-hosted option, no open API
- No open-source compliance framework exists for prediction market audit trails
- No tool maps state-by-state regulatory status with automated compliance scoring
- No tool detects suspicious trading patterns (wash trading, coordinated manipulation) specific to prediction markets

## Success Metrics
- Working CLI that ingests trade data and produces compliance reports
- State-by-state regulatory status tracker (all 50 US states + key international)
- Risk scoring engine for suspicious trading patterns
- Audit trail export in regulator-ready format (CSV/JSON)
- 80%+ test coverage

## Lens Research Support
Opportunity #3 from Lens Daily Intel 2026-06-22: "Prediction Market Compliance Platform" — Polymarket scandal breaking today, CFTC enforcement ramping, zero open-source compliance tools exist.
