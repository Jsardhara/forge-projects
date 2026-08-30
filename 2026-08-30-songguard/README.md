# songguard

Zero-dependency, offline, no-LLM **lyric copyright-infringement screener** for AI-generated
music pipelines and label compliance gates. It screens a candidate lyric against a reference
catalog and reports verbatim / near-verbatim "sampling" risk.

Built from Lens Op #1 (2026-08-30): Sony Music + Warner v Anthropic IP suit → copyright
screening middleware for gen-AI music. The portfolio had AI-content detection (contentmark) and
model-license parsing (licguard), but nothing screens **candidate content against a reference
corpus** for infringement. This fills that gap.

## How it works

1. **Normalize** — lowercase; letters/digits/apostrophes kept (`"don't"` stays one token);
   whitespace/punctuation collapsed.
2. **Shingles** — bigram token shingles; windows with zero content words (all function words)
   are dropped so coincidence windows like `("and","the")` never produce a signal.
3. **Three signals per reference:**
   - **containment** — fraction of the input's shingles actually present in the reference
     (sampling exposure).
   - **jaccard** — shingle-set intersection/union (whole-song near-duplicates).
   - **longest_common_phrase** — the longest contiguous shared word run (note-for-note sampling).

## Verdicts

Per-reference severity from the worst signal, aggregate verdict is severity-dominant (worst
single reference wins):

| Signal | CLEAR | REVIEW | INFRINGE |
|--------|-------|--------|----------|
| longest shared phrase | < 6 tokens | 6–15 tokens | ≥ 16 tokens |
| containment | < 0.15 | 0.15–0.35 | ≥ 0.35 |
| jaccard | < 0.25 | 0.25–0.50 | ≥ 0.50 |

`score` (0–100) = `100 * (0.5·max_containment + 0.3·max_jaccard + 0.2·min(longest_run,24)/24)`,
clamped; used for the CI magnitude gate.

## Install

```bash
pip install .
```

## Usage

```bash
# Human-readable screen of a lyric against a catalog directory
songguard screen my_llm_lyric.txt catalog/

# JSON
songguard screen my_llm_lyric.txt catalog/ --json

# Read the lyric from stdin
cat my_lyric.txt | songguard screen - catalog/

# CI gate: exit 1 on any non-CLEAR verdict or score >= 60, exit 2 on error
songguard check my_llm_lyric.txt catalog/
songguard check my_llm_lyric.txt catalog/ --threshold 50
```

`reference` may be a single lyric file or a directory of `*.txt/*.md/*.lrc/*.ly/*.srt` files.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | clear (or a successful `screen`) |
| 1 | `check` found REVIEW/INFRINGE risk or score ≥ threshold |
| 2 | input/reference read error |

## Tests

```bash
pip install pytest && pytest tests/ -v
```

36+ tests cover the three fixture classes (verbatim sampling → INFRINGE; original vs unrelated
catalog → CLEAR; short common-phrase coincidence → stays CLEAR), paraphrase-cover risk, JSON
validity, and CI exit codes.

## Honest limits

- Lyric-level only: it compares **text lyrics**, not audio waveforms. It does NOT do acoustic
  fingerprinting or C2PA media stamping (future work Lens scoped).
- Heuristic, not legal advice. A REVIEW/INFRINGE is a *signal for human adjudication*, not a
  finding of infringement.
- Similarity is token-exact after normalization; heavy paraphrase (synonym rewrites) that changes
  most tokens may under-report, which is why longest-phrase + containment both count.