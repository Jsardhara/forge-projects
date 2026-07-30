# restrictbot — US Physical AI Trade Restriction Compliance Scanner

**Check product descriptions against the USG 2026-07-29 ban on foreign-made humanoids, robot dogs, and solar inverters.**

An automated compliance scanner for physical AI hardware companies, robotics importers, and trade compliance teams. Scans product descriptions against restricted categories and returns PASS/WARN/FAIL with specific triggers.

## Quick Start

```bash
pip install restrictbot

# Check a single product
restrictbot check "AtlasBot" "Next-generation humanoid robot for warehouse"

# CI gate — exit 1 on FAIL
restrictbot check "AtlasBot" "humanoid robot" --ci

# Scan a CSV of products
restrictbot scan products.csv --ci

# List restricted categories
restrictbot categories
```

## Restricted Categories

| Category | Level | Description |
|----------|-------|-------------|
| Humanoid Robot | **BANNED** | Full humanoid robots |
| Robot Dog / Quadruped | **BANNED** | Biomimetic quadrupeds |
| Solar Inverter | **BANNED** | Photovoltaic inverters |
| Humanoid Upper Torso | **RESTRICTED** | Telepresence / upper-torso systems |
| Biomimetic Robot | **RESTRICTED** | Snake, hexapod, octopus robots |
| Powered Exoskeleton | **MONITORED** | Wearable robots |
| Autonomous Ground Vehicle | **MONITORED** | Small UGVs |

## CLI Commands

### `restrictbot check <name> <description>`
Check a single product. Returns PASS/WARN/FAIL with specific category triggers.

Options: `--json` (JSON output), `--ci` (exit 1 on FAIL)

### `restrictbot scan <file.csv>`
Batch scan a CSV with `name,description` columns.

Options: `--json`, `--ci`

### `restrictbot categories`
List all restricted categories and their keywords.

## Python API

```python
from restrictbot import scan_product

result = scan_product("AtlasBot", "Humanoid robot for warehouse")
print(f"Verdict: {result.verdict.value}  Score: {result.score}")
for f in result.findings:
    print(f"  [{f.verdict.value}] {f.category}: {f.reason}")
```

## License

MIT