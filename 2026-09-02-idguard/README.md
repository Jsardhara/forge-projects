# idguard — Identity-Exposure & Breach-Notification Compliance Screener

Scan an arbitrary breach dump and learn **what identity assets actually leaked**, how
severe each record is, and what your notification obligation is. All-stdlib Python.
Zero external dependencies. CI-friendly exit code.

Built from Lens Intel 2026-09-02 Opportunity 3 — the FBI probe into a service that
sold **153M+ US drivers' licenses** (KrebsOnSecurity). The recurring incident gap:
responders get a dump file and have no offline way to (a) detect/validate exposed
identity assets (SSNs, per-state US drivers'-license numbers) and (b) translate the
exposure into a breach-notification plan.

## Why this, not BreachSentinel

BreachSentinel (2026-06-30) answers *"did my known email leak?"* against HIBP + local
dumps. **idguard answers a different question:** *"scan this dump — what identity assets
leaked, how severe, and what must I notify?"*

| | BreachSentinel | idguard |
|---|---|---|
| Job | per-identity exposure monitor (HIBP + dumps) | dump-content PII forensics + notification triage |
| Input | an email to check | a raw dump (csv/json/jsonl) |
| SSN validation | escalate-if-labeled | validates area/group/serial SSA rules |
| US DL per-state format | no | yes (classic formats, state-hints) |
| Notification compliance | no | 50-state matrix + remediation steps |

## Install

```bash
cd 2026-09-02-idguard
pip install .
```

## Usage

### Scan a dump

```bash
# CSV / JSON / JSONL; '-' reads stdin
idguard scan breach.csv
idguard scan records.json --json
idguard scan dump.jsonl --threshold 5
```

Exit codes (CI gate): `0` = OK, `1` = HIGH-severity records met threshold,
`2` = CRIT-severity records present (valid SSN + name + DOB, or valid SSN + name/DOB).

### Generate breach-notification triage

```bash
idguard notify --states CA,TX,NY --subscribers 1200 --residents 900 \
  --summary "valid SSNs exposed: 128, DL state hints: CA, TX"
idguard notify                # all 50 states + DC
```

`notify` emits a reference table: mandatory AG/regulator report, notification window,
required-content checklist (common across states), and remediation steps for affected
individuals. **This is reference triage, not legal advice** — always verify the current
statute and your entity type (state law vs GLBA/FCRA/HIPAA) before notifying.

## How detection works

- **SSN** — authoritative classic SSA validation: 9 digits, area 001–899 (no 000, 666,
  900+), group not 00, serial not 0000, plus known advertising/invalid numbers
  (078-05-1120, 219-09-9999, etc.).
- **US drivers' license** — classic (pre-Real-ID) published state formats for ~16 states
  (`patterns.py` `_STATE_DL_PATTERNS`), plus a generic 7–17 char fallback. A raw number
  can match several states, so we report candidate states as **hints, never an identity
  claim**; severities are composed from the *combination* of assets, not a lone number.
- **Severity composition** (confidence-weighted, honest):
  - `CRIT` — validated SSN + name + DOB, or validated SSN + (name or DOB)
  - `HIGH` — validated SSN alone; or DL-hint + name + DOB (no SSN)
  - `MEDIUM` — DL-hint + name; exposed password; DOB
  - `LOW` — email / phone alone

## Extending

Add a state's classic DL format to `_STATE_DL_PATTERNS` in `src/idguard/patterns.py`
and add a test. The notification matrix lives in `src/idguard/notify.py` (`_STATE` dict).

## License / ethics

MIT. The tool detects *patterns in data you already have*. It performs no live
exfiltration and reaches out to no breach marketplaces. Format coverage is
representative, not exhaustive; treat it as triage, verify before acting.