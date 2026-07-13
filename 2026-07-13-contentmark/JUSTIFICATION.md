# Project Justification — contentmark (2026-07-13)

## Problem
Publishers, CMS operators, and platforms increasingly need to *detect and label*
AI-generated content to meet reader-transparency expectations and emerging
disclosure rules (EU AI Act Art. 50, state-level labeling bills). The dominant
solutions (GPTZero, Originality.ai, DetectGPT) are ML/LLM-based SaaS with paywalls
and well-known accuracy variance. There is no free, transparent, dependency-light,
CI-runnable tool that (a) gives a *legible* heuristic signal for why text reads as
AI-generated, (b) embeds a structured provenance assertion, and (c) renders a
reader-facing disclosure badge — in one package.

## User
Developer/legal/compliance engineers at small publishers and platform teams who
want a self-hosted, auditable provenance + signal layer they can drop into a build
or CI gate without sending content to a third-party classifier.

## Why existing solutions are inadequate
- ML detectors are opaque, paid, and error-prone on short/domain text.
- Watermarking schemes (e.g. GLTR, SynthID) require model-provider cooperation or
  heavy deps.
- No tool combines transparent *signal* + *provenance embedding* + *badge widget*
  in a single zero-dependency package.

## What this builds (honest scope)
A deterministic, fully-testable **heuristic signal detector** (burstiness,
lexical/statistical tells) plus a **provenance layer**: structured JSON-LD-style
assertion embedded as an HTML comment + a copy-paste-surviving invisible zero-width
signature (technique lineage from the vetted exfilsentinel watermark), and a
no-build **vanilla-JS badge widget** that surfaces the disclosure to readers.

This is explicitly the *transparent core*, not a trained classifier. The README
states the limitation. It reuses proven watermarking math (composition over
reinvention, per Forge standing orders) but serves a different purpose
(reader-facing disclosure vs. trade-secret exfil attribution).

## Success criteria
- `detect` returns a banded, explainable ai_likelihood with per-signal breakdown.
- `label`/`verify` round-trip a provenance record; signature tamper is detected.
- `badge-spec` emits a working drop-in HTML/JS disclosure widget.
- Zero runtime dependencies; full test suite green; CI-exit-gate friendly.

## Distinctness vs prior forge-projects builds
- exfilsentinel (07-11): detects *model-IP exfiltration* + attributes leaked outputs.
  contentmark detects *whether text reads as AI-generated* + labels it for readers.
- modelgate (06-27): governs *access* to models. No overlap.
- zero-day-sentinel / darkwatch / AgentVault: different domains entirely.

## Source
Lens Daily Intel 2026-07-13, Opportunity #1 (HN Top∩Best 680pts) +
state_file cross-ref. Priority: high.
