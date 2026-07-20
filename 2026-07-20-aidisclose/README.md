# aidisclose — AI-Disclosure Compliance Gap Analyzer

Answer two questions every org deploying AI now faces:

1. **Which AI-disclosure mandates apply to me?**
2. **Where am I non-compliant right now?**

`aidisclose` is a zero-dependency, citation-backed compliance gap analyzer. It
maps an organization's AI use (sector, jurisdictions, use cases) to the disclosure
mandates that apply, computes an overall 0–100 gap score and risk band, and can
act as a CI / pre-launch compliance gate.

> Not legal advice. The bundled dataset is a structured knowledge base of public
> mandates; verify against counsel before relying on it.

## Why this exists

Through 2026, AI-disclosure rules moved from proposal to enforcement across many
jurisdictions at once (NYC Local Law 144, Colorado AI Act, EU AI Act transparency
chapter, California AB 3030/AB 453, Illinois BIPA, plus fresh 2026 proposals on
AI listing images and social-media demasking). Enterprise GRC suites (OneTrust,
TrustArc) are closed and expensive. `aidisclose` is the portable, scriptable,
version-controllable alternative — distinct from `darkwatch` (website dark-pattern
scanning), `licguard` (model-license checks), and `contentmark` (AI-text detection).

## Install

```bash
pip install .
```

## Usage

### List tracked mandates

```bash
aidisclose list
aidisclose list --status proposed      # watch-only items
```

### Analyze an org profile

```bash
# via flags
aidisclose analyze --name "Acme Hiring Co" \
  --jurisdictions US-NY --sectors employment --ai_uses hiring

# or via a JSON profile
aidisclose analyze --profile org.json --format json
```

Profile JSON shape:

```json
{
  "name": "Acme Hiring Co",
  "sectors": ["employment"],
  "jurisdictions": ["US-NY"],
  "ai_uses": ["hiring"],
  "implemented": ["candidate_disclosure"],
  "reference_date": "2026-07-20"
}
```

- `sectors`: employment, real_estate, healthcare, retail, finance, government,
  education, …
- `jurisdictions`: US-NY, US-CO, US-CA, US-IL, EU, AU-VIC, …
- `ai_uses`: hiring, content_generation, listing_generation, biometric,
  facial_recognition, emotion_recognition, surveillance, recommendation,
  customer_support

### CI gate

`check` exits **non-zero when a blocking (critical) disclosure gap exists** — wire
it into CI or a pre-launch hook:

```bash
aidisclose check --profile org.json && echo "no blocking gaps"
```

## How scoring works

For every **in-force** mandate whose scope matches the profile, each obligation is
weighted by severity (critical 10 / high 6 / medium 3 / low 1). The overall gap
score is:

```
score = 100 * (sum of unmet obligation weights)
            / (sum of all applicable obligation weights)
```

Risk bands: `<20` LOW · `20–49` MEDIUM · `50–79` HIGH · `≥80` CRITICAL.
Proposed/upcoming mandates are reported as **monitored** (watch-only) and never
scored. A mandate is a **blocking** gap if any of its unmet obligations is
critical.

## Library use

```python
from aidisclose.models import OrgProfile
from aidisclose.engine import analyze
from aidisclose.report import to_json

profile = OrgProfile(name="Acme", jurisdictions=("US-NY",),
                     sectors=("employment",), ai_uses=("hiring",))
report = analyze(profile)
print(to_json(report))
```

## Project layout

```
src/aidisclose/
  models.py   # frozen dataclasses (Mandate, Obligation, OrgProfile)
  rules.py    # curated, citation-backed mandate dataset
  engine.py   # applicability + gap scoring
  report.py   # markdown + JSON report formatting
  cli.py      # list / analyze / check
tests/        # pytest suite (models, rules, engine, report, cli)
```

## License

MIT
