# npm-shield — npm v12 Install Script Auditor & Allowlist Generator

## Problem
npm v12 (July 2026) introduces breaking security defaults: `allowScripts` defaults to `off`, blocking all preinstall/install/postinstall/prepare scripts. Every company using npm must audit their dependencies and generate allowlists for v12 compliance.

## What It Does
1. **Scan** — Parse package-lock.json (v1/v2/v3) and identify all packages with install scripts
2. **Classify** — Risk scoring: HIGH (multiple scripts), MEDIUM (single), LOW (publish-only)
3. **Allowlist** — Generate the authorization.authorizedPackages config for package.json
4. **Report** — Rich-formatted tables or JSON output for CI/CD pipelines

## Quick Start
```bash
pip install npm-shield
npm-shield scan .
npm-shield allowlist .
```

## Test Results
- 27/27 tests passing
- TDD approach with pytest

## Architecture
See ARCHITECTURE.md for module layout and design decisions.

## License
MIT
