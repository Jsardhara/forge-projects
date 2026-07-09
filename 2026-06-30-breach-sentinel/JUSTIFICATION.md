# Project Justification: BreachSentinel

## What problem does this solve?

On June 29, 2026, over one million passports were leaked online from a cannabis dispensary systems company (Nefos/Puffpal). This follows a pattern of escalating identity data breaches where personal documents, credentials, and PII appear in dark web paste sites, breach dumps, and unauthorized databases with **no automated detection** for affected individuals or security teams.

Existing solutions fall into two categories:
- **haveibeenpwned.com** — manual, email-only, requires proactive checking; no monitoring or alerting
- **Enterprise tools (SpyCloud, Constella, Recorded Future)** — $10K+/year, aimed at Fortune 500 SOC teams

There is **no open-source, low-cost tool** that:
1. Scans multiple breach sources (HIBP API, paste sites, DNS dumps) for leaked credentials
2. Monitors email/phone/passport/SSN exposure over time
3. Generates actionable alerts with breach context (what leaked, when, severity)
4. Supports both individual users (self-hosted) and teams (compliance monitoring)

## Who is the user?

- **Security engineers** at SMBs who can't afford enterprise breach detection but need to know if their org's credentials are leaking
- **Individual privacy-conscious users** who want automated monitoring of their personal data exposure
- **Compliance officers** who need audit trails for data breach regulatory requirements (GDPR 72hr notification, state breach notification laws)

## Why are existing solutions inadequate?

1. **haveibeenpwned** requires manual checking — no continuous monitoring, no alerting, no team view
2. **Enterprise tools** cost more than entire cloud infrastructure for most companies
3. **Dark web monitoring** services are opaque black boxes with false-positive fatigue
4. No tool combines email breach detection + credential strength assessment + exposure scoring in one open package

## How we'll measure success

- Detects known-leaked emails via HIBP API (verified test data)
- Generates severity-scored breach reports (critical/high/medium/low)
- CLI returns proper exit codes for CI/CD integration
- Tests cover: parsing, scoring, deduplication, CLI smoke, integration
- All 100% stdlib Python — zero external deps, runs anywhere
