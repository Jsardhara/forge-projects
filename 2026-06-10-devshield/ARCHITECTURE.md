# DevShield Architecture

## Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  CLI (Click)│────▶│  Scanner     │────▶│  Package Parsers │
│             │     │  (Orchestra) │     │  (npm, pip,      │
└──────┬──────┘     └──────┬───────┘     │   pyproject)     │
       │                   │              └─────────────────┘
       │                   │
       │                   ▼
       │            ┌──────────────┐
       │            │  AI Tooling  │
       │            │  Database    │
       │            └──────────────┘
       │                   │
       │                   ▼
       │            ┌──────────────┐     ┌─────────────────┐
       │            │  Advisory    │────▶│  GitHub Advisory │
       │            │  Client      │     │  DB API          │
       │            └──────────────┘     └─────────────────┘
       │                   │
       ▼                   ▼
┌─────────────────────────────────┐
│         Scan Report             │
│  ┌──────────┐ ┌──────────────┐ │
│  │  Table   │ │    JSON      │ │
│  │ Reporter │ │   Reporter   │ │
│  └──────────┘ └──────────────┘ │
└─────────────────────────────────┘
```

## Module Breakdown

### `cli.py` — Command Line Interface
- Click-based CLI with `scan`, `check`, and `init` subcommands
- Supports `--json`, `--all`, `--fail-on`, `--token` flags
- Exit codes: 0 (clean), 1 (vulnerabilities found above threshold)

### `scanner.py` — Core Scanning Engine
- `Scanner` class orchestrates the full scan pipeline
- `ScanReport` aggregates results across all packages
- `ScanResult` represents a single package's scan outcome
- Filters non-AI packages by default (override with `--all`)

### `package_managers.py` — Dependency Parsers
- `NpmLockParser`: Parses `package-lock.json` (v1, v2, v3 formats)
- `PipRequirementsParser`: Parses `requirements.txt`
- `PyprojectParser`: Parses `pyproject.toml` dependencies
- `find_dependencies()`: Auto-detects all dep files in a directory

### `advisory.py` — GitHub Advisory DB Client
- `AdvisoryClient` queries the GitHub Advisory REST API
- Rate-limited to 1 req/sec for unauthenticated use
- `AdvisoryResult` contains per-package vulnerability data
- Supports filtering by ecosystem (npm, pip)

### `ai_tooling_db.py` — AI Tooling Package Registry
- Maintains a curated list of known AI tooling packages
- Organized by ecosystem (npm, pip)
- `is_ai_tooling()` for fast lookup
- Extensible: add new packages as the AI tooling landscape grows

### `reporters.py` — Output Formatters
- `TableReporter`: Rich terminal tables with severity coloring
- `JsonReporter`: JSON output for CI/CD pipeline integration

### `config.py` — Configuration Management
- Loads `.devshield.yaml` from project root
- CLI flags override config file values
- Supports: `scan_all`, `fail_on`, `severity_threshold`, `output_format`, `ignore_packages`, `ignore_advisories`

## Data Flow

1. User runs `devshield scan .`
2. CLI loads config from `.devshield.yaml` (if present)
3. `Scanner` calls `find_dependencies()` to extract deps from lockfiles
4. For each dependency, `Scanner` checks `is_ai_tooling()` — skips non-AI unless `--all`
5. For AI packages, `AdvisoryClient.search_by_package()` queries GitHub Advisory DB
6. Results aggregated into `ScanReport`
7. Reporter renders output (table or JSON)
8. Exit code set based on `--fail-on` threshold

## Extending DevShield

### Adding New Package Managers
Create a new parser class in `package_managers.py`:

```python
class GemfileParser:
    @staticmethod
    def parse(gemfile: Path) -> list[Dependency]:
        # ... parse Gemfile.lock ...
        return deps
```

Then add it to `find_dependencies()`.

### Adding New AI Tooling Packages
Edit `ai_tooling_db.py` and add to the `AI_TOOLING_PACKAGES` dict:

```python
AI_TOOLING_PACKAGES["npm"].append("new-ai-package")
```

### Adding New Output Formats
Create a new reporter in `reporters.py`:

```python
class SarifReporter:
    def render(self, report: ScanReport) -> str:
        # ... generate SARIF JSON ...
        return json_data
```

## Rate Limiting

The GitHub Advisory API has rate limits:
- **Unauthenticated**: 60 requests/hour
- **Authenticated**: 5,000 requests/hour

DevShield rate-limits requests to 1/second to stay within unauthenticated limits. For team use, set `GITHUB_TOKEN` or `github_token` in config.

## Security Considerations

- DevShield is **read-only** — it never modifies your dependencies
- API tokens are read from environment variables or config, never hardcoded
- Rate limiting prevents accidental API abuse
- All network requests use HTTPS
