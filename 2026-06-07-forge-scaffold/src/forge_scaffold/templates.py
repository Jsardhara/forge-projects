"""Jinja2 templates for forge-scaffold project generation."""

from jinja2 import Template

GITIGNORE_TEMPLATE = Template("""__pycache__/
*.pyc
.venv/
*.db
*.sqlite3
.env
*.egg-info/
""")

PYPROJECT_TEMPLATE = Template("""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{{ slug }}"
version = "0.1.0"
description = "{{ description }}"
requires-python = ">=3.11"
dependencies = [
    {% for dep in dependencies %}"{{ dep }}",
    {% endfor %}]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
]

[project.scripts]
{{ entry_point }} = "{{ module }}.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
""")

PYPROJECT_NO_ENTRY_TEMPLATE = Template("""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{{ slug }}"
version = "0.1.0"
description = "{{ description }}"
requires-python = ">=3.11"
dependencies = [
    {% for dep in dependencies %}"{{ dep }}",
    {% endfor %}]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
""")

README_TEMPLATE = Template("""# {{ name }}

{{ description }}

## Quick Start

```bash
cd {{ slug }}
/c/Users/jyot2/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pip install -e ".[dev]"
pytest tests/ -v
```

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for design decisions and system overview.

## Justification

See [JUSTIFY.md](./JUSTIFY.md) for why this project exists.
""")

JUSTIFY_TEMPLATE = Template("""# Project Justification: {{ name }}

## Problem
{{ problem }}

## Existing Solutions
{{ existing_solutions }}

## Proposed Solution
{{ proposed_solution }}

## Impact Criteria
{{ impact_criteria }}

## Why now
{{ why_now }}
""")

ARCHITECTURE_TEMPLATE = Template("""# Architecture: {{ name }}

## Overview
{{ overview }}

## Tech Stack
{{ tech_stack }}

## Key Design Decisions
{{ design_decisions }}

## Failure Modes
{{ failure_modes }}
""")

INIT_PY_TEMPLATE = Template("""\"\"\"{{ name }} - {{ description }}\"\"\"
""")

CLI_TEMPLATE = Template("""\"\"\"CLI entry point for {{ slug }}.\"\"\"

import click


@click.group()
def main():
    \"\"\"{{ name }} CLI.\"\"\"
    pass


@main.command()
def hello():
    \"\"\"Say hello.\"\"\"
    click.echo("Hello from {{ name }}!")
""")

TEST_TEMPLATE = Template("""\"\"\"Tests for {{ slug }}.\"\"\"

from {{ module }}.cli import main
from click.testing import CliRunner


def test_cli_invocation():
    runner = CliRunner()
    result = runner.invoke(main, ["hello"])
    assert result.exit_code == 0
    assert "Hello" in result.output
""")
