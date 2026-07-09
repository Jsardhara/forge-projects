# BreachSentinel

Open-source **breach exposure monitoring** for individuals and teams. Scan
multiple breach sources for leaked credentials and identity documents, score
exposure severity, and emit actionable alerts — with a SQLite audit trail.

**All-stdlib Python. Zero external dependencies. Runs anywhere.**

## Why

On 2026-06-29, over a million passports and SSNs leaked from a dispensary
systems company (Nefos/Puffpal). This follows a pattern of escalating identity
breaches where personal documents appear in dumps with **no automated
detection** for affected people or security teams.

- [haveibeenpwned.com](https://haveibeenpwned.com) requires manual, email-only
  checking — no continuous monitoring, no team view.
- Enterprise tools (SpyCloud, Constella, Recorded Future) cost $10K+/year.

BreachSentinel is the missing middle: open, low-cost, automated, and extensible.

## Features

- **Multi-source scanning** — HaveIBeenPwned v3 (with k-anonymity Pwned
  Passwords) and local breach dumps / paste files (JSON or JSONL).
- **Exposure scoring** — 0–100 score combining breach count, data sensitivity
  (email < phone < password < API key < SSN/passport), and recency.
- **Severity alerts** — `info / low / medium / high / critical`, with identity
  document exposure always escalated to at least HIGH.
- **Idempotent persistence** — SQLite store dedupes by deterministic breach id;
  safe to re-scan repeatedly.
- **CI-friendly CLI** — non-zero exit code when alerts fire.

## Install

```bash
cd 2026-06-30-breach-sentinel
pip install .
```

## Usage

### Scan from a local breach dump (offline, no API key needed)

```bash
breachsentinel scan --label "Alice" --email alice@example.com \
  --local sample_breaches.json --json
```

### Scan against HaveIBeenPwned

```bash
export HIBP_API_KEY="your-key"   # https://haveibeenpwned.com/API/Key
breachsentinel --db myorg.db scan --label "Team Acme" --email sec@acme.com --hibp
```

### Report across all tracked identities

```bash
breachsentinel --db myorg.db report
```

### Show recent alerts

```bash
breachsentinel --db myorg.db alerts --limit 20
```

## Local breach file format

JSON list or JSONL. One object per breach observation:

```json
{
  "identity_value": "alice@example.com",
  "breach_type": "email",          // email|phone|password|api_key|credit_card|ssn|passport|other
  "breach_name": "Adobe 2013",
  "breach_date": "2013-10-04",     // optional
  "description": "..."             // optional
}
```

`identity_value` may be a string or a list (same breach, multiple values).

## Project status

Self-improving / personal-security category. Distinct from prior forge-projects
(RegShield = regulatory scanning, MCP Shield = MCP security, ZeroDaySentinel =
0-day CVE detection). No open-source breach *exposure monitor* exists in the
repo. Production hardener: add the live HIBP path to a real key in CI, add
paste-site scrapers, and wire recurring scans into Sentinel.

## License

MIT
