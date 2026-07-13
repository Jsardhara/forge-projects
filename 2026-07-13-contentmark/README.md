# contentmark

Transparent, zero-dependency **AI-content signal detector + provenance/labeling
toolkit**. contentmark helps publishers and platforms *measure* and *disclose*
AI-generated content without sending text to a third-party classifier.

> **Scope & honesty:** contentmark is a **deterministic, transparent heuristic**
> detector — it measures writing-style tells, not semantic meaning. It is *not* a
> trained ML classifier (those are paid/opaque and error-prone on short text). Use
> it as a signal + disclosure layer, not as proof. Always pair with human judgment
> and a disclosed labeling policy.

## What it does

1. **`detect`** — analyze text and return a banded `ai_likelihood`
   (`human` → `possibly_ai` → `likely_ai` → `very_likely_ai`) with a per-signal,
   fully-explainable breakdown. CI-friendly exit code (1 if `very_likely_ai`).
2. **`label`** — embed a **structured provenance** assertion (as an HTML comment)
   **plus** an invisible, copy-paste-surviving **signature** (zero-width Unicode
   technique, with a FNV-1a checksum for tamper detection).
3. **`verify`** — check whether text carries a provenance marker, whether the
   comment and invisible signature agree, and whether anything was tampered.
4. **`badge`** — emit a drop-in **reader-facing disclosure badge** (HTML + CSS +
   vanilla-JS), no build step.

## Install

```bash
pip install .
```

Zero runtime dependencies (Python 3.10+).

## CLI

```bash
# Detect AI-content signals in a file
contentmark detect article.md
contentmark detect - --json            # stdin, JSON output

# Label text with provenance + invisible signature
contentmark label draft.md --label ai_generated --tool "AcmeWriter" --model "gpt-x" > labeled.md

# Verify provenance on labeled text
contentmark verify labeled.md

# Emit a disclosure badge (html | css | js | all)
contentmark badge --label ai_generated --tool "AcmeWriter" --part all
```

## Library

```python
from contentmark import detect, embed, verify, Provenance, ProvenanceLabel
from contentmark import badge_html, badge_css, badge_script

report = detect(text)
print(report.explain())              # human-readable breakdown
print(report.band.value)             # 'likely_ai'

prov = Provenance(rid="cm_abc123", label=ProvenanceLabel.AI_GENERATED, tool="AcmeWriter")
labeled = embed(text, prov)
v = verify(labeled)
assert v.valid and not v.tampered
```

## How the signals work

| Signal | What it measures | Why it matters |
|---|---|---|
| `burstiness` | variation in sentence length | machine prose tends to be uniform |
| `repetition` | type-token ratio | generated text reuses vocabulary |
| `connector_frequency` | discourse connectors ("moreover", "furthermore") | over-enumerated transitions are a known tell |
| `low_perplexity_words` | ratio of very common words | flat diction |
| `filler_density` | filler words ("essentially", "overall") | hedging cadence |
| `enumeration_density` | numbered/bulleted + "first/second/finally" | structured output patterns |
| `sentence_uniformity` | CV of sentence length | machine cadence |

All signals are weighted, normalized to `[0,1]`, and **explainable**. Short inputs
(<40 words) are never accused — the band is forced to `human`.

## Provenance signature (copy-paste survival)

The invisible signature uses four zero-width Unicode characters with **strict role
separation** (technique lineage from the vetted `exfilsentinel` watermark, 2026-07-11):
- framing only: `U+200B` (start) / `U+200C` (end)
- data bits only: `U+200D` = 1 / `U+2060` = 0

Because no character is reused across roles, a `0`-bit can never be mistaken for
framing (the delimiter/bit collision bug class is avoided). A FNV-1a checksum is
embedded, so edits to the marker are detectable. The signature survives copy-paste
even if the visible text or the HTML comment is modified/removed.

## Relationship to other tooling

- **vs. ML detectors (GPTZero, etc.):** transparent + free + local; less accurate
  on short/domain text by design — it's a disclosure aid, not a classifier.
- **vs. `exfilsentinel` (forge-projects 2026-07-11):** that tool *defends model IP*
  via output watermarking for attribution; contentmark *labels content for readers*.
  Different purpose; shared watermarking math (composition over reinvention).

## License

MIT
