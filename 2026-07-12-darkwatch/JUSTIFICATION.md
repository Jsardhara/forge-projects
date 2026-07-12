# Project Justification — darkwatch (Dark-Pattern Compliance Scanner)

## Problem
A regulatory cascade is forcing subscription and consumer-UX compliance across the
US and EU simultaneously, and the obligation lands on product/legal teams who have
no cheap, repeatable way to *measure* their exposure:

- **NYC Local Law** bans deceptive subscription practices (roach-motel cancel flows,
  pre-checked add-ons) — #1 BEST signal on HN 2026-07-10 (631 pts).
- **EU DSA Art. 25** requires platforms to avoid "addictive design" patterns,
  especially those targeting minors — EU Commission found Instagram/Facebook in
  breach (274 pts BEST).
- **FT / TechCrunch** report Big Tech facing EU consumer-protection fines; cookie
  stuffing (Phia) and forced continuity are active enforcement themes.

The pain is real *today*: a SaaS or e-commerce team shipping a checkout or
subscription flow can unknowingly violate 3+ regimes at once. Audits are manual,
expensive ($10k+ consultations), and happen too late (post-launch).

## User
In-house product/engineering/legal at SaaS + subscription e-commerce companies
(per Lens revenue model: $49–299/mo SaaS per domain). Also useful to investors/
acquirers doing UX-diligence, and to regulators/advocates building evidence.

## Why existing solutions are inadequate
- Manual legal audits: slow, costly, not runnable in CI.
- Generic "accessibility/lint" tools (axe, Lighthouse): check a11y + perf, not
  dark-pattern/regulatory heuristics.
- Browser-recorder SaaS (for the full crawl): heavy, paid, and overkill for the
  detection logic — the *heuristics* are the valuable, reusable asset, and they are
  testable on static HTML with zero dependencies.

## What we build
A zero-dependency (stdlib-only) Python library + CLI that scans an HTML page (or
saved checkout/cancel-flow HTML) for 8 dark-pattern heuristic rules mapped to 4
regulations (NYC Subscriptions, EU DSA Art. 25, EU UCPD, FTC Negative-Option),
produces findings with severity + evidence + regulation references, an aggregate
compliance band, a per-regulation checklist, and text/markdown/JSON reports. Exit
code 1 on NON_COMPLIANT makes it a drop-in CI compliance gate.

## Success criteria
- 8 rules, each with ≥1 green test proving it fires on a crafted fixture and stays
  silent on a clean fixture (negation-filtered where required).
- End-to-end CLI: `scan` a fixture → correct band + exit code; `checklist` → per-
  regulation pass/fail.
- Zero external dependencies; installs cleanly via hatchling; pytest green.
- Distinct from existing forge builds (exfilsentinel, AgentVault, MCP Shield).
