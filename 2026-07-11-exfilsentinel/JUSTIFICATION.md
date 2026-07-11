# Project Justification: exfilsentinel

## Problem
On 2026-07-10 Apple sued OpenAI over alleged trade-secret theft by ex-employees (1,078 HN TOP∩BEST + TechCrunch), the latest in a wave of AI-IP extraction litigation (Anthropic–Alibaba 28.8M-exchange campaign, 06-25). The attack pattern is consistent: a trusted employee with legitimate model access uses that access to *bulk-extract* proprietary model outputs, weights, or fine-tunes — typically concentrated around offboarding. Existing tooling governs *who may call a model* (e.g. our own `modelgate`, 06-27) but is blind to *abuse of already-granted access*. There is no lightweight, self-contained control that (a) detects extraction behavior from API access logs and (b) embeds attributable provenance into model outputs so leaked IP can be traced back to origin.

## User
Enterprise AI security teams and IP/legal counsel — specifically during employee offboarding, insider-risk reviews, and incident response.

## Why existing solutions are inadequate
- `modelgate` (06-27) is a *pre-access* governance gate (approve/deny + classify risk). It does not observe post-access *behavior*.
- Commercial LLM-gateway vendors (LiteLLM, Portkey) log traffic but ship no exfil-specific behavioral scoring or output-provenance watermarking for IP-theft defense.
- LLM watermarking research (SynthID, Kirchenbauer) targets *detectability of AI-generated text*, not *attribution of stolen outputs to a specific org/model/leak event*.
- No single OSS tool bundles behavioral extraction detection + survivable output-provenance watermarking for the trade-secret-defense use case.

## What this build does (distinct layer)
1. **Extraction detector** — multi-signal weighted scoring over API access events: volume burst, repetitive-prompt (bulk scraping), completion-heavy harvest, rate spike, sensitive/proprietary model access, download-pattern (weights/datasets), off-hours, and offboarding-window boost. Classifies BENIGN / SUSPICIOUS / EXFILTRATION. Allowlist credit for sanctioned bulk jobs.
2. **Output-provenance watermark** — embeds an invisible (zero-width Unicode) provenance record (org_id | model | timestamp | nonce) into model output text that survives plain-text copy-paste, with `embed` / `verify` / `detect`. Lets a leaked document be traced to its origin.

## Success criteria
- All signals have unit tests; normalization + classification boundaries verified.
- Watermark round-trips (embed→verify) and `detect` returns false on clean text, true on watermarked text.
- CLI `scan` / `embed` / `verify` / `detect` work end-to-end.
- Zero external dependencies; stdlib only; installable wheel.
