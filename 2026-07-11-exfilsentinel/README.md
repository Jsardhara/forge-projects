# exfilsentinel

AI model-access **exfiltration detector** + **output-provenance watermarking** for
trade-secret defense.

Built in response to the 2026-07-10 Apple v. OpenAI trade-secret litigation (and the
broader AI-IP-extraction wave). `modelgate` (06-27) governs *who may call a model*;
`exfilsentinel` watches *abuse of already-granted access* and lets leaked IP be traced
back to its origin.

- **Zero dependencies** (stdlib only). Installable wheel.
- **Behavioral detection** over API access logs — multi-signal weighted scoring.
- **Output-provenance watermark** — invisible (zero-width Unicode) record that
  survives plain-text copy-paste, so a leaked document can be attributed to
  org | model | time | nonce.

## Install
```bash
pip install .
```

## Detection — signals
| Signal | Weight | Trigger |
|--------|--------|---------|
| `volume_burst` | 0.25 | total completion tokens extracted |
| `repetitive_prompt` | 0.20 | low prompt-template diversity (bulk scraping) |
| `completion_heavy` | 0.15 | completion/total token ratio skew |
| `rate_spike` | 0.15 | requests/sec far above human pace |
| `sensitive_model_access` | 0.20 | access to `ft:`/`internal`/`private`/`proprietary` models |
| `download_pattern` | 0.30 | `/files`, `download`, `export`, `dataset`, `weights` endpoints |
| `off_hours` | 0.08 | activity between 00:00–06:00 |
| `offboarding_window` | 0.20 | activity in the 30 days before offboarding |

Normalization: `risk = Σ(wᵢ·rawᵢ) / Σ(wᵢ)` over triggered signals only.
Offboarding boosts risk ×1.25; allowlisted actors get −0.30 credit.
Classification: **BENIGN** ≤0.25, **SUSPICIOUS** ≤0.65, **EXFILTRATION** >0.65.

`scan` exits non-zero on EXFILTRATION (CI gate).

## Watermark API
```python
from exfilsentinel import embed, verify, detect
from exfilsentinel import ProvenanceRecord
from datetime import datetime, timezone

rec = ProvenanceRecord("acme", "ft:acme-prod", datetime.now(timezone.utc), "nonce-xyz")
wm = embed("confidential model output", rec)
assert detect(wm.text) is True
assert verify(wm.text).nonce == "nonce-xyz"
```

## CLI
```bash
exfilsentinel scan  --events events.json --actor mallory [--offboarding ISO] [--allowlisted]
exfilsentinel embed --text "..." --org acme --model ft:acme [--nonce N] [--out file]
exfilsentinel verify --text-file wm.txt
exfilsentinel detect --text "pasted leaked doc"
```

## Tests
```bash
pip install pytest && pytest tests/ -v
```

## Limitations
- Watermark is *attribution*, not *leak-prevention* — it survives copy-paste but not
  heavy paraphrase/translation.
- Detection is heuristic; tune weights/thresholds for your environment.
