# LicGuard

**Offline ML/AI open-weight model license compliance checker.**

LicGuard turns a *model + intended use* into a deterministic
`COMPLIANT` / `NEEDS_REVIEW` / `NON_COMPLIANT` verdict — no network, no legal
review queue. Built for teams wiring up multi-model routers / self-hosting
open-weight models who need a pre-deploy license gate.

## Install

```bash
pip install .
```

## Usage

```bash
# List the built-in license database
licguard list

# Check a single model + use case
licguard check --model llama-3.1-8b --commercial --monthly-active-users 10000000
licguard check --model mistral-7b --commercial --redistribute
licguard check --model llama-3.1-8b --commercial --use-case "customer support chatbot"

# Scan a deployment manifest
licguard scan --manifest manifest.json
```

`python -m licguard ...` also works.

### Manifest format

```json
{
  "models": [
    {"model": "mistral-7b", "use": {"commercial": true}},
    {"model": "llama-3.1-70b", "use": {"commercial": true, "monthly_active_users": 2000000000}},
    {"model": "inkling", "use": {"commercial": true}}
  ]
}
```

## Exit codes

- `0` — compliant (or needs-review, which is allowed-with-warning)
- `1` — non-compliant (use as a CI / deploy gate)

## Honesty note

License terms in the built-in database are encoded from publicly known license
facts as of mid-2026 and are **intentionally conservative**. Canonical license
text is always authoritative — LicGuard prints a reminder to that effect. Models
with no published license (e.g. newly announced open-weights releases) are
surfaced as `NEEDS_REVIEW` rather than guessed.

## Scope

Grounded licenses include: Llama 3.1 Community, Gemma Terms, Mistral/Mixtral
(Apache-2.0), Qwen2.5 (Apache-2.0), DeepSeek (MIT), Phi (MIT + MS AUP), GLM-4
(Apache-2.0), Kimi K2/K3 (open-weights). Extend `licguard/licenses.py` to add
more.
