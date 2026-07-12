# darkwatch — Dark-Pattern Compliance Scanner

Zero-dependency (stdlib-only) scanner that detects dark patterns and
consumer-protection red flags in subscription / checkout / UX flows, mapped to
four regulations:

- **NYC Local Law** — Deceptive Subscription Practices (roach-motel cancel flows)
- **EU DSA Art. 25** — Addictive design / minor protection
- **EU UCPD** — Unfair Commercial Practices (pre-checked boxes, disguised ads)
- **FTC Negative-Option / Dark-Pattern Rule** — forced continuity

Runs on static HTML — no browser, no network, no external deps. Designed as a
drop-in **CI compliance gate**: `darkwatch scan` exits non-zero on
`NON_COMPLIANT`.

## Why

A regulatory cascade is forcing subscription + consumer-UX compliance across the
US and EU simultaneously (NYC ban, EU DSA Art. 25 addictive-design findings, FT
consumer-protection fines). Product/legal teams have no cheap, repeatable way to
*measure* exposure before launch. darkwatch turns 8 dark-pattern heuristics into
a testable, automatable control.

## Install

```bash
pip install .
# or, for development:
pip install ".[dev]"
```

## Usage

```bash
# Scan a saved HTML file (text report)
darkwatch scan path/to/checkout.html

# JSON for piping into CI / dashboards
darkwatch scan path/to/checkout.html --format json

# Per-regulation pass/fail checklist
darkwatch checklist path/to/checkout.html

# Markdown report to a file
darkwatch report path/to/checkout.html --out report.md

# Read from stdin (e.g. captured via Playwright/curl)
curl -s https://example.com/checkout | darkwatch scan -

# List the 8 registered rules
darkwatch rules
```

### CI gate

```bash
darkwatch scan checkout.html --format json && echo "COMPLIANT" || echo "NON-COMPLIANT"
```

Exit code `1` when the aggregate band is `NON_COMPLIANT`
(≥1 critical finding **or** ≥3 findings total).

## Detection rules

| Rule | Heuristic | Regulation | Severity |
| --- | --- | --- | --- |
| `roach_motel_cancel` | Signup flow with no cancel link, or cancel routed through a phone call | NYC Subscriptions | high |
| `prechecked_optin` | Default-checked box with consent/marketing language | EU UCPD | high |
| `forced_continuity` | Free-trial + auto-renewal without clear negation disclosure | FTC Negative-Option | medium |
| `confusing_language` | "Unsubscribe" phrased as a charge/penalty | EU UCPD | medium |
| `fake_urgency` | Countdown/timer or scarcity ("only N left", "ends tonight") | EU DSA | medium |
| `mismatched_consent` | Marketing box labeled only as "terms/conditions" | EU UCPD | medium |
| `disguised_ad` | Sponsored/promoted element without "advertisement" disclosure | EU UCPD | low |
| `minor_addictive` | Daily-reward / streak / spin-to-win loops (suppressed by age gate) | EU DSA | medium |

## Python API

```python
from darkwatch import scan_html, to_text

result = scan_html(open("checkout.html", encoding="utf-8").read(), url="checkout.html")
print(to_text(result))
print(result.band)  # ComplianceBand.COMPLIANT | NEEDS_REVIEW | NON_COMPLIANT
```

## Tests

```bash
pytest tests/ -v
```

All 34 tests cover: each rule firing on a crafted fixture **and** staying silent on
a clean fixture (with negation-filter and age-gate exceptions), banding thresholds,
the per-regulation checklist, and the CLI exit-code contract.

## License

MIT
