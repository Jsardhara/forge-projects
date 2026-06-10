# Design Brainstorm: DevShield — AI Coding Supply Chain Security Scanner

## Interface Type
CLI Tool + CI/CD Plugin (Developer Security Tool)

## Target User
- Development teams using AI coding assistants (Claude Code, Cursor, Copilot, Gemini CLI)
- Security engineers responsible for supply chain security
- DevOps engineers integrating security scanning into CI/CD pipelines
- Individual developers who want to audit their AI tooling dependencies

## Problem Statement
Microsoft's open-source Azure repos were hacked with password-stealing malware targeting AI coding app users (Claude Code, Gemini CLI, VS Code). Developers have zero visibility into whether their AI tooling dependencies are compromised. Existing tools (npm audit, pip-audit) don't specifically track AI tooling packages or monitor the GitHub Advisory DB for new AI-tooling-specific vulnerabilities in real-time.

## Reference Analysis
1. **GitHub Advisory DB** — authoritative source for known vulnerabilities, free API
2. **npm audit / pip-audit** — existing dependency scanners, but not AI-tooling-aware
3. **Snyk / Dependabot** — commercial solutions, expensive, not focused on AI tooling
4. **Socket.dev** — supply chain security for npm, but not AI-specific

## Layout Architecture
- CLI-first design: `devshield scan`, `devshield audit`, `devshield watch`
- CI/CD integration via GitHub Action
- JSON output for machine consumption, human-readable table for terminal
- Config file (`.devshield.yaml`) for project-specific settings

## Design Decisions
- Language: Python (cross-platform, easy pip install)
- API: GitHub Advisory DB REST API (no auth required for public advisories)
- Package managers: npm (via `package-lock.json`), pip (via `requirements.txt` or `pyproject.toml`)
- Output: Rich terminal tables + JSON for CI/CD
- Extensible: Plugin architecture for new package managers

## Component List
- [x] `scanner.py` — Core scanning engine
- [x] `advisory.py` — GitHub Advisory DB client
- [x] `package_managers/npm.py` — npm lockfile parser
- [x] `package_managers/pip.py` — pip requirements parser
- [x] `reporters/table.py` — Rich terminal output
- [x] `reporters/json.py` — JSON output for CI/CD
- [x] `cli.py` — Click-based CLI
- [x] `config.py` — Config file loader
- [x] `ai_tooling_db.py` — Known AI tooling packages database

## Anti-Patterns We're Avoiding
- Not a generic vulnerability scanner (focus on AI tooling)
- Not a SaaS dashboard (CLI-first, local-first)
- Not requiring API keys for basic functionality
- Not bloated with dependencies (minimal deps: requests, click, rich, pyyaml)
