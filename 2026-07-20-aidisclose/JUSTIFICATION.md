# Project Justification: aidisclose (AI-Disclosure Compliance Gap Analyzer)

## Problem
Through 2026, AI-disclosure mandates have moved from proposal to enforcement across
many jurisdictions at once: NYC Local Law 144 (automated employment decision tools),
the Colorado AI Act, the EU AI Act transparency chapter (Art. 13), California AB 3030
(synthetic-content labeling), and a wave of fresh 2026 proposals (NYC Mayor's AI
listing-image disclosure, Victoria AU social-media demasking, SF nudify-app takedowns,
Kaiser-nurse surveillance scrutiny). Organizations — especially small/mid ones — have
no cheap, auditable way to answer two questions: *"Which of these mandates apply to
me?"* and *"Where am I non-compliant right now?"*.

## User
In-house compliance owners, startup founders, and engineering leads who deploy AI
(hiring tools, listing/content generators, biometrics, surveillance) and must
self-assess disclosure obligations without buying a $50k/yr GRC platform.

## Why existing solutions are inadequate
- Enterprise GRC suites (OneTrust, TrustArc, Securiti) are closed, expensive, and
  API/portal-bound — no portable, scriptable, version-controllable CLI.
- `darkwatch` (07-12) scans a *website's HTML* for dark patterns — different input,
  different obligation set.
- `licguard` (07-17) checks *model license* permissibility — not regulatory disclosure.
- `contentmark` (07-13) *detects AI-generated text* and watermarks it — a detector,
  not an applicability/gap engine.
None of these answer "which laws apply to my org + what's my gap." aidisclose fills
that exact layer: a curated, citation-backed mandate dataset + an applicability and
gap-scoring engine, runnable as a CLI or imported as a library. Zero dependencies.

## Success criteria
- `aidisclose list` enumerates all tracked mandates with jurisdiction + status.
- `aidisclose analyze --profile org.json` returns applicable mandates, per-mandate
  unmet obligations, an overall 0-100 gap score, and a risk band.
- `aidisclose check` exits non-zero when a blocking (critical) disclosure gap exists,
  making it usable as a CI / pre-launch compliance gate.
- All logic covered by deterministic tests (datasets integrity, applicability,
  gap scoring, reporting, CLI).
