# forge-scaffold

CLI tool that automates the Forge daily build scaffolding workflow. Reduces 30-45 minutes of mechanical work to a single command.

## Problem

Every day, the Forge agent spends significant time on repetitive scaffolding before writing any actual project code:
- Creating directories
- Writing .gitignore, pyproject.toml, JUSTIFY.md, ARCHITECTURE.md, README.md
- Creating test scaffolding
- Installing dependencies, running tests
- Git add/commit/push
- Updating INDEX.md
- Publishing to the agent bus

This is pure overhead. `forge-scaffold` automates all of it.

## Install

```bash
cd 2026-06-07-forge-scaffold
env -u PYTHONHOME /c/Users/jyot2/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pip install -e ".[dev]"
```

## Usage

### Scaffold a new project
```bash
# Basic Python library
forge-scaffold -- push new my-cool-lib --type python-lib --description "A cool library"

# CLI tool
forge-scaffold new my-cli --type cli-tool --description "A useful CLI"

# FastAPI service
forge-scaffold new my-api --type fastapi-service --description "A REST API"
```

### Check repo health
```bash
forge-scaffold doctor
```

### Rebuild INDEX.md
```bash
forge-scaffold index
```

### Show repo status
```bash
forge-scaffold status
```

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for design decisions, module breakdown, and failure modes.

## Modules

- `scaffold.py` — Core scaffolding logic: validates slugs, checks duplicates, generates files
- `repo.py` — Repo state: scans projects, updates INDEX.md, git operations
- `doctor.py` — Health checks: validates .gitignore, test naming, required files
- `bus_integration.py` — Agent bus integration: publishes code-ready, reads research
- `cli.py` — Click CLI entry point: `new`, `doctor`, `index`, `status` commands
- `templates.py` — Jinja2 templates for all generated files

## Tests

```bash
pytest tests/ -v
```

## Justification

See [JUSTIFY.md](./JUSTIFY.md) for why this project exists.
