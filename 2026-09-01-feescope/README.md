# feescope

**Ad-spend surcharge & fee-opaqueness audit scanner** — a deterministic, offline,
zero-dependency CLI that reconciles advertising invoice line items against a trusted
"verified" spend and flags hidden surcharges, opaque fee buckets, fee-stacking, and
aggregate fee-ratio / reconciliation drift.

Built from Lens daily-intel 2026-09-01 **Opportunity 3**: the FTC's lawsuit accusing
Amazon of running a "secret ad surcharge scheme" (TechCrunch, 2026-09-01). Advertisers
and agencies lack open tooling to detect when billed media spend diverges from what a
platform confidentially confirms — feescope makes that a 30-second CLI check.

## Why

- **Problem today:** Programmatic/performance invoices bury "platform fee", "service
  fee", "admin" line items with no transparent subcategory, and platforms can bill more
  than the verified spend they confirm elsewhere. Agencies reconcile this by hand or
  pay for expensive SaaS.
- **Who:** in-house media buyers, performance marketers, FTC-disclosure‑conscious
  agencies, ad-audit shops.
- **Existing gap:** the pipeline already has `darkwatch` (consumer dark-patterns),
  `costrecon` (AWS cloud billing), `capalarm` (AI plan-cap spend) — none reconcile
  third-party ad-invoice fee lines against verified spend. This is genuinely uncovered.

## Install

```bash
pip install --no-cache-dir .
pytest tests/ -v   # optional, needs pytest
```

Requires Python ≥ 3.10, stdlib only.

## Input

A CSV or JSON file of billing line items, or stdin via `-`.

**CSV** (header required):

```csv
line_id,description,amount,verified,category,attached_to
L1,Programmatic media buy,1000.00,1000.00,media,
F1,Platform fee,250.00,,fee,B1
L2,Verified placement,120.00,100.00,media,
```

**JSON** (array of items, or a wrapper with invoice metadata):

```json
{
  "invoice_id": "INV-2026-0901",
  "expected_total": 1250.00,
  "items": [
    {"line_id": "L1", "description": "Media placement", "amount": 1000.00, "verified": 1000.00, "category": "media"},
    {"line_id": "F1", "description": "Platform fee", "amount": 250.00, "category": "fee", "attached_to": "B1"}
  ]
}
```

Fields: `line_id`, `description`, `amount`, `verified` (optional independent confirmed
spend), `category` (`media` | `fee` | `discount` | `tax` | `other`), `attached_to`
(optional base purchase id that a fee hangs off — used for stacking detection).

## CLI

```bash
feescope scan invoice.csv            # human-readable
feescope scan invoice.json --json    # machine-readable
cat invoice.csv | feescope scan -    # stdin
feescope check invoice.csv           # CI gate: exit 1 on non-CLEAR or score >= 60
```

### Signals

| Code | Signal | Severity |
|------|--------|----------|
| FEE-001 | Opaque/unexplained fee line (no transparent subcategory) | WARN |
| FEE-002 | Billed > independently-verified spend beyond 0.5% (**the "secret surcharge"**) | FLAG |
| FEE-003 | Fee-stacking: multiple fee lines on one base purchase | WARN |
| FEE-004 | Aggregate fees/billed ratio exceeds 0.20 | WARN |
| FEE-005 | Sum of line items vs expected total: drift >0.5% WARN, >5% FLAG | WARN/FLAG |

### Verdict & score

- **Verdict is severity-dominant**: the worst single finding decides `CLEAR` / `WARN` /
  `FLAG` (a hidden surcharge FLAG dominates any number of WARNs).
- **Score (0–100)** is the weighted magnitude (WARN +25, FLAG +55, capped 100) — used
  only by the `check` gate threshold, never to override the dominant verdict.

### Exit codes

- `scan`: 0 on success, 2 on read/parse error.
- `check`: 0 if `CLEAR` **and** score < threshold; 1 otherwise; 2 on read error.

## Thresholds (configurable)

| Flag | Default |
|------|---------|
| `--tolerance` | `0.005` (0.5%) |
| `--flag-tolerance` | `0.05` (5%) |
| `--max-fee-ratio` | `0.20` |
| `check --threshold` | `60.0` |

## Anti-patterns this avoids

- **No fabricated spend/margins** — every signal derives from line items you provide.
- **No "verified" scare-stats** — FEE-002 only fires when you supply a `verified` value.
- **Severity-dominant verdict** — never upgrades to FLAG purely from stacked WARN
  arithmetic.

## Tests

Run `pytest tests/ -v` with the Hermes venv Python. 17 cases cover each signal's
positive + negative direction, severity dominance, score magnitude, clean invoices,
and config overrides.