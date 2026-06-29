# Project Justification: zkage-verify

## Problem
The KIDS Act (US, June 2026) and EU Chat Control proposals mandate age verification for internet access. Current solutions fall into two broken categories:
1. **ID upload** (Yoti, Jumio) — destroys privacy, creates honeypots of identity data
2. **Self-declaration** — trivially bypassed, non-compliant

Platforms face a hard regulatory deadline with no privacy-respecting tooling. **Who pays the price?** Every user who must hand over their ID to read a recipe, and every platform that becomes a data breach liability.

## User
- **Primary**: SaaS/platform compliance teams (age-gating required by KIDS Act, EU Chat Control, UK OAIC)
- **Secondary**: Privacy-focused apps (Telegram, Signal, dating apps, gaming) that need to prove compliance without collecting PII

## Why Existing Solutions Are Inadequate
- **Yoti/Jumio**: Collect and store full identity documents — regulatory liability, breach target
- **Stripe Identity**: Payment-focused, not a general age verification primitive
- **Apple's Age Range API**: iOS-only, requires parental consent flow, doesn't satisfy KIDS Act requirements for all users
- **ZK-proof libraries (circom/snarkjs)**: Require Node.js toolchain, circuit compilation, trusted setup — too heavy for most Python/small teams

**Gap**: A lightweight, stdlib-only Python library that provides the *cryptographic primitives* for privacy-preserving age verification (Pedersen commitments, range proofs, nullifier schemes) that platforms can integrate without a ZK-circuit compiler.

## Existing Forge Builds (Distinct From)
- `model-router` — LLM routing, unrelated
- `edugate` — school AI access control, different domain
- `predictguard` — prediction market compliance, different domain
- `prbouncer` — PR spam detection, different domain

**None** cover ZK-based identity verification.

## Success Criteria
- Platform can verify "user is ≥13/≥18" without learning exact birthdate
- Nullifier scheme prevents double-counting/linkability across services
- Tests prove commitment binding + range proof correctness
- CLI demo shows full flow: issue → verify → check nullifier

## Source
- Lens Daily Intel 2026-06-29, Opportunity #2 (KIDS Act + age attribution + EU Chat Control)
- EFF: https://www.eff.org/deeplinks/2026/06/kids-act-would-require-age-checks-get-online
- nonogra.ph: https://nonogra.ph/age-verification-is-just-a-precursor-to-attribution-of-speech-06-29-2026
