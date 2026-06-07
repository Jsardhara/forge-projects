# Project Justification: forge-scaffold

## Problem
Every day, Forge (the build agent) spends 30-45 minutes on purely mechanical scaffolding work before writing a single line of actual project code: creating directories, writing .gitignore, pyproject.toml, JUSTIFY.md, ARCHITECTURE.md, README.md, creating test scaffolding, installing dependencies, running initial tests, git add/commit/push, updating INDEX.md, and publishing to the agent bus. This is pure overhead that adds no value to the final product.

## Existing Solutions
- **cookiecutter**: General-purpose project templating. Doesn't integrate with the forge-projects workflow (bus checking, INDEX.md, build plans). Templates are static and require separate maintenance.
- **Copier**: Similar to cookieter, same limitations.
- **Manual scaffolding**: What Forge does today. Repetitive, error-prone, and wastes the agent's time on mechanical work.

None of these solutions understand the forge-projects workflow: checking the agent bus for research, reading Lens's intel, checking for duplicate projects in the repo, auto-updating INDEX.md, or publishing code-ready to the bus.

## Proposed Solution
`forge-scaffold` — a Python CLI tool that automates the entire forge-projects daily build scaffolding workflow. Takes a project slug and type, generates the complete folder structure with all required files pre-filled, optionally runs the initial git workflow, updates INDEX.md, and publishes to the agent bus.

Key innovation: it's not just a template generator — it's **workflow-aware**. It knows about the forge-projects repo structure, the agent bus, and the daily build lifecycle.

## Impact Criteria
- Reduces daily build scaffolding time from 30-45 min to <5 min
- Eliminates common errors (missing .gitignore, wrong test file names, forgotten INDEX.md updates)
- Deployable and usable by the next daily build

## Why now
The forge-projects repo has 14 projects and counting. The scaffolding overhead is compounding. Today's build is the right time to build the tool that makes all future builds faster.
