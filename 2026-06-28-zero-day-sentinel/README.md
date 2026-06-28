# ZeroDaySentinel

**GitHub 0-Day Vulnerability Detection & Patch Automation**

On June 27-28, 2026, anonymous mass 0-day vulnerability drops began appearing on GitHub at unprecedented scale. Security teams need automated tooling to detect when their dependencies are hit by undisclosed vulnerability disclosures.

ZeroDaySentinel scans GitHub repositories for 0-day exploit indicators, fingerprints the disclosed vulnerabilities, matches them against your dependency graph, and generates actionable patch suggestions.

## Features

- **0-Day Detection**: Identifies exploit/0-day repositories using topic analysis, README pattern matching, and heuristic classification
- **Vulnerability Fingerprinting**: Extracts CVE IDs, affected products/versions, CPEs, and severity from exploit repos
- **Dependency Matching**: Matches fingerprints against your dependency graph with version range support
- **Patch Generation**: Generates actionable patch suggestions with confidence scores and effort estimates
- **Multiple Output Formats**: Text and JSON reports
- **Stdlib Only**: Zero external dependencies for core logic

## Installation

```bash
pip install zerosentinel
```

## Quick Start

```bash
# Run demo scan
zerosentinel scan --demo

# Run demo match against sample dependencies
zerosentinel match --demo

# JSON output
zerosentinel scan --demo --format json
```

## Architecture

```
zerosentinel/
├── models.py      — Data models (ExploitRepo, VulnerabilityFingerprint, PatchSuggestion)
├── scanner.py     — 0-day detection engine (pattern matching, classification, severity)
├── matcher.py     — Dependency graph matching (version ranges, aliases, CPEs)
├── patchgen.py    — Patch suggestion generator (templates by vuln type)
├── reporter.py    — Report generator (text + JSON)
└── cli.py         — CLI interface
```

## Detection Signals

| Signal | Description |
|--------|-------------|
| Topic analysis | Checks for `0day`, `exploit`, `poc`, `rce`, etc. |
| README patterns | 20+ regex patterns for exploit indicators |
| CVE extraction | Identifies CVE IDs in text |
| Product matching | 50+ known product aliases |
| Version parsing | Range matching, prefix matching, exact matching |
| Severity assessment | Critical/High/Medium/Low based on exploit type |

## Patch Types

| Type | Description |
|------|-------------|
| `version_pin` | Upgrade to patched version |
| `config_change` | Modify configuration for mitigation |
| `code_fix` | Modify code to address vulnerability |
| `workaround` | Temporary mitigation until patch available |

## Example Output

```
========================================================================
  ZeroDaySentinel — 0-Day Vulnerability Detection Report
========================================================================

Scan Time:        2026-06-28 15:30:00 UTC
Repos Scanned:    3
Scan Duration:    0.001s
Matches Found:    2
Critical:         1

------------------------------------------------------------------------
  DETECTED VULNERABILITIES
------------------------------------------------------------------------

  [1] [CRITICAL] RCE vulnerability detected in linux from repository anonymous/cve-2026-xxxx-linux
      Product:     linux
      Versions:    6.8.0
      Type:        rce

  [2] [HIGH]     Authentication Bypass vulnerability detected in apache from repository bikini/exploitarium
      Product:     apache
      Type:        authentication_bypass
```

## License

MIT
