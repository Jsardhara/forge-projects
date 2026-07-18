# Project Justification — LicGuard

## Problem
The 2026 open-weight model wave (Kimi K3, Inkling, GLM-5.2, Qwen, DeepSeek, Llama 3.x,
Gemma, Mistral, Phi) made self-hosted and routed LLM deployments mainstream. But every
open-weight model ships under a *different* license with real deployment constraints:
Llama's Community License forbids certain use cases and requires a license + revenue
share above 700M monthly users; Gemma/Mistral/Qwen/DeepSeek/Phi carry Apache-2.0 / MIT
terms with acceptable-use restrictions; some newly announced models (e.g. Inkling) have
no published license text yet. Teams wiring up "Open Model Gateway"-style routers
(Lens Opportunity #1, 2026-07-17) routinely ship a model to production without checking
whether that use is permitted. There is no fast, offline, scriptable way to ask
*"can I deploy model X for purpose Y, commercially, and redistribute it?"*

## User
ML platform engineers, indie devs, and founders building on open-weight models; compliance
owners who must sign off on model usage. Anyone standing up a multi-model router or
self-hosting a model and needing a pre-deploy license gate.

## Why existing solutions are inadequate
- `license-expression` / `spdx-license-list` only parse SPDX identifiers — they do not
  encode *model-specific* constraints (AUPs, user-threshold clauses, acceptable-use bans).
- Legal review is slow and not scriptable into a CI/deploy gate.
- Model hubs (HuggingFace) show a license tag but not a deployment-fit verdict for a
  specific use case.
LicGuard fills the gap: an offline, deterministic engine that turns a model + intended
use into a COMPLIANT / NEEDS_REVIEW / NON_COMPLIANT verdict with human-readable reasons,
plus a CLI and a `scan` mode for deployment manifests.

## Success criteria
- `licguard list` enumerates known licenses offline.
- `licguard check --model llama-3.1-8b --use commercial` returns a deterministic verdict.
- Llama commercial use >700M MAU correctly flags NON_COMPLIANT; <=700M is COMPLIANT.
- `licguard scan manifest.json` evaluates every model in a deployment manifest.
- Full test suite green; works with zero network access.

## Grounding / honesty note
License terms stored in the built-in database are encoded from publicly known license
facts as of mid-2026 and are intentionally conservative. The tool prints a reminder that
canonical license text is authoritative. Unknown/newly-announced models are surfaced as
NEEDS_REVIEW rather than guessed.
