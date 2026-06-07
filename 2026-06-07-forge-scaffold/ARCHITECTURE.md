# Architecture: forge-scaffold

## Overview
`forge-scaffold` is a Python CLI tool that automates the Forge daily build scaffolding workflow. It reads the agent bus for research context, checks the forge-projects repo state, scaffolds a complete project folder, and handles the initial git workflow + INDEX.md update + bus publish.

## Tech Stack
- **Python 3.11+** (host Python on the Windows machine)
- **click** for CLI (lightweight, no heavy dependencies)
- **jinja2** for templating (lightweight, flexible)
- **bus.py** (existing agent bus module) for publish/read

## Folder Structure
```
forge-scaffold/
  .gitignore
  JUSTIFY.md
  ARCHITECTURE.md
  README.md
  pyproject.toml
  src/
    forge_scaffold/
      __init__.py
      cli.py          # Click CLI entry point
      scaffold.py     # Core scaffolding logic
      templates.py    # Jinja2 template definitions
      repo.py         # Repo state (git, INDEX.md)
      bus.py          # Agent bus integration
      doctor.py       # Health checks
  tests/
    test_scaffold.py
    test_repo.py
    test_doctor.py
    test_cli.py
```

## Key Design Decisions

### 1. Templates as Python strings, not files
Jinja2 templates are defined as Python string constants in `templates.py`. This keeps the tool self-contained — no need to ship template files alongside the installed package. The trade-off is slightly less readable templates, but the simplicity wins.

### 2. Repo state from filesystem, not git commands
Instead of shelling out to `git`, we read the repo directory structure directly to check for existing projects. Git operations (add/commit/push) are done via subprocess since there's no pure-Python git library worth the dependency.

### 3. Bus integration via existing bus.py
We import the existing `bus.py` module from `C:\Users\jyot2\AppData\Local\hermes\scripts\` rather than reimplementing the bus protocol.

### 4. Safe defaults
- Never overwrites existing files (checks before writing)
- Never pushes without explicit `--push` flag
- Validates project slug format (lowercase, hyphens, no special chars)

## Commands

```
forge-scaffold new <slug> [--type python-lib|fastapi-service|cli-tool] [--push]
  Scaffold a new project in the forge-projects repo.

forge-scaffold doctor
  Check the forge-projects repo for common issues.

forge-scaffold index
  Rebuild INDEX.md from scratch by scanning the repo.

forge-scaffold status
  Show repo state: last project, total count, uncommitted changes.
```

## Failure Modes
- Missing .gitignore → auto-creates with standard patterns
- Duplicate slug → aborts with error message showing existing project
- Bus unavailable → warns but continues (bus is optional for local dev)
- Git push fails → aborts with instructions to push manually
