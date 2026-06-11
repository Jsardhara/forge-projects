# Architecture: npm-shield

## Overview

```
┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│  CLI (click) │────▶│  Scanner      │────▶│  Rich Report │
│              │     │  (core logic) │     │  (tables)    │
│  npm-shield  │     │               │     │              │
│  scan        │     │  - parse v1/v2/v3         │  - summary   │
│  allowlist   │     │  - find scripts           │  - risk      │
│              │     │  - classify risk          │  - findings  │
│              │     │  - generate allowlist     │  - JSON      │
└──────────────┘     └───────────────┘     └──────────────┘
```

## Module Layout

```
src/npm_shield/
├── __init__.py
├── cli.py          # Click CLI: scan, allowlist commands
├── scanner.py      # Core lockfile parser + risk classifier
├── allowlist.py    # npm v12 authorization config generator
├── report.py       # Rich-formatted output + JSON renderer
└── errors.py       # Custom exceptions
```

## Lockfile Parsing Strategy

Supports npm lockfile versions 1, 2, and 3:

| Version | Package Key | Root Entry | Dev Detection |
|---------|-------------|------------|---------------|
| v1      | `dependencies` | `""` | Heuristic (devDependencies in root) |
| v2      | `dependencies` or `packages` | `""` | Heuristic |
| v3      | `packages` | `""` | Heuristic |

## Risk Classification

- **HIGH**: 2+ install scripts (preinstall, install, postinstall, prepare)
- **MEDIUM**: 1 install script
- **LOW**: Only publish-only scripts (prepublish, prepublishOnly, postpublish)

## Allowlist Output Format

Generates the `authorization.authorizedPackages` block for `package.json`:

```json
{
  "authorization": {
    "authorizedPackages": {
      "esbuild@0.21.0": ["postinstall", "preinstall"],
      "husky@8.3.7": ["install"]
    }
  }
}
```

## Testing

- 27 tests across 3 test files
- TDD approach: tests written before implementation
- Covers: scanner, allowlist, report, edge cases (missing files, invalid JSON)
