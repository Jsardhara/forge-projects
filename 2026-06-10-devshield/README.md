# DevShield — AI Coding Supply Chain Security Scanner

> Detect compromised AI tooling dependencies before they compromise your codebase.

## The Problem

In June 2026, Microsoft's open-source Azure repositories were hacked with password-stealing malware targeting users of AI coding tools like Claude Code, Gemini CLI, and VS Code extensions. The attackers injected malicious code into widely-used packages — a classic supply chain attack on the AI development ecosystem.

**Developers have zero visibility into whether their AI tooling dependencies are compromised.**

Existing tools like `npm audit` and `pip-audit` don't specifically track AI tooling packages or provide real-time monitoring of new AI-tooling-specific vulnerabilities.

## What DevShield Does

DevShield is a CLI tool that:

1. **Scans** your project's dependency files (`package-lock.json`, `requirements.txt`, `pyproject.toml`)
2. **Identifies** known AI tooling packages (Claude Code, OpenAI, LangChain, etc.)
3. **Checks** each package against the GitHub Advisory Database for known vulnerabilities
4. **Reports** findings in human-readable tables or JSON for CI/CD pipelines

## Quick Start

```bash
# Install
pip install devshield

# Scan current directory (AI tooling packages only)
devshield scan .

# Scan all packages (not just AI tooling)
devshield scan . --all

# Output JSON for CI/CD
devshield scan . --json

# Check specific packages
devshield check openai anthropic langchain --ecosystem pip

# Create config file
devshield init
```

## Installation

```bash
pip install devshield
```

Or from source:

```bash
git clone https://github.com/Jsardhara/forge-projects
cd forge-projects/2026-06-10-devshield
pip install -e ".[dev]"
```

## CLI Reference

### `devshield scan [PATH]`

Scan a project directory for vulnerable dependencies.

| Flag | Description |
|------|-------------|
| `--all` | Scan all packages, not just AI tooling |
| `--json` | Output JSON (for CI/CD integration) |
| `--fail-on` | Fail on severity: `low`, `medium`, `high`, `critical` |
| `--token` | GitHub API token (increases rate limit) |

Exit codes: `0` = no vulnerabilities above threshold, `1` = vulnerabilities found.

### `devshield check PACKAGES...`

Check specific packages for known vulnerabilities.

```bash
devshield check openai @anthropic-ai/claude-code --ecosystem npm
```

### `devshield init`

Create a `.devshield.yaml` config file in the project directory.

## Configuration

Create `.devshield.yaml` in your project root:

```yaml
# Scan all packages (not just AI tooling)
scan_all: false

# Output format: table or json
output_format: table

# Fail CI/CD on this severity or higher
fail_on: high

# GitHub API token (optional, increases rate limit from 60 to 5000/hr)
# github_token: GITHUB_TOKEN

# Packages to ignore
ignore_packages:
  - some-package

# Advisory IDs to ignore
ignore_advisories:
  - GHSA-xxxx-yyyy

# Severity threshold for reporting
severity_threshold: low
```

## CI/CD Integration

### GitHub Actions

```yaml
name: DevShield Security Scan
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install devshield
      - run: devshield scan . --json --fail-on high
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Pre-commit Hook

```yaml
repos:
  - repo: local
    hooks:
      - id: devshield
        name: DevShield Security Scan
        entry: devshield scan . --fail-on high
        language: system
        pass_filenames: false
```

## Monitored AI Tooling Packages

### npm / Node.js
- `@anthropic-ai/claude-code`, `@anthropic-ai/sdk`
- `openai`
- `@google/generative-ai`
- `langchain`, `@langchain/core`
- `llama-index`

### Python / pip
- `anthropic`, `openai`, `google-generativeai`
- `langchain`, `langchain-core`, `langchain-community`
- `llama-index`
- `huggingface-hub`, `transformers`

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed technical documentation.

## License

MIT
