"""Core scaffolding logic for forge-scaffold."""

import datetime
import os
import re
import shutil
from pathlib import Path
from typing import Optional

from .templates import (
    GITIGNORE_TEMPLATE,
    PYPROJECT_TEMPLATE,
    PYPROJECT_NO_ENTRY_TEMPLATE,
    README_TEMPLATE,
    JUSTIFY_TEMPLATE,
    ARCHITECTURE_TEMPLATE,
    INIT_PY_TEMPLATE,
    CLI_TEMPLATE,
    TEST_TEMPLATE,
)

# Default forge-projects repo location
DEFAULT_REPO = Path("C:/Users/jyot2/jarvis/projects/forge-projects-repo")

# Scripts directory for bus integration
SCRIPTS_DIR = Path("C:/Users/jyot2/AppData/Local/hermes/scripts")

VALID_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

PROJECT_TYPES = {
    "python-lib": {
        "has_cli": False,
        "dependencies": [],
        "description": "A Python library with tests",
    },
    "fastapi-service": {
        "has_cli": False,
        "dependencies": ["fastapi>=0.115", "uvicorn>=0.30"],
        "description": "A FastAPI service",
    },
    "cli-tool": {
        "has_cli": True,
        "dependencies": ["click>=8.0"],
        "description": "A CLI tool",
    },
}


class ScaffoldError(Exception):
    """Raised when scaffolding fails."""
    pass


def validate_slug(slug: str) -> None:
    """Validate project slug format."""
    if not VALID_SLUG_RE.match(slug):
        raise ScaffoldError(
            f"Invalid slug '{slug}': must be lowercase letters, numbers, and hyphens only"
        )


def check_duplicate(slug: str, repo_path: Path) -> None:
    """Check if a project with this slug already exists."""
    today = datetime.date.today()
    prefix = today.isoformat()  # YYYY-MM-DD
    # Check for any folder matching YYYY-MM-DD-{slug}
    for item in repo_path.iterdir():
        if item.is_dir() and item.name.endswith(f"-{slug}"):
            raise ScaffoldError(
                f"Project '{slug}' already exists: {item.name}/ in repo"
            )


def scaffold_project(
    slug: str,
    project_type: str = "python-lib",
    name: Optional[str] = None,
    description: str = "TODO: describe this project",
    problem: str = "TODO: describe the problem",
    repo_path: Optional[Path] = None,
    push: bool = False,
) -> Path:
    """Scaffold a new project in the forge-projects repo.

    Returns the path to the created project directory.
    """
    validate_slug(slug)

    if project_type not in PROJECT_TYPES:
        raise ScaffoldError(
            f"Unknown type '{project_type}'. Choose from: {', '.join(PROJECT_TYPES)}"
        )

    repo = repo_path or DEFAULT_REPO
    check_duplicate(slug, repo)

    today = datetime.date.today()
    folder = repo / f"{today.isoformat()}-{slug}"

    config = PROJECT_TYPES[project_type]
    display_name = name or slug.replace("-", " ").title()
    module_name = slug.replace("-", "_")

    # Create directory structure
    pkg_dir = folder / "src" / module_name
    tests_dir = folder / "tests"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    # --- Write files ---

    # .gitignore
    (folder / ".gitignore").write_text(GITIGNORE_TEMPLATE.render())

    # pyproject.toml
    if config["has_cli"]:
        entry_point_module = f"{module_name}.cli"
        pyproject = PYPROJECT_TEMPLATE.render(
            slug=slug,
            description=description,
            dependencies=config["dependencies"],
            entry_point=slug.replace("-", "_"),
            module=entry_point_module,
        )
    else:
        pyproject = PYPROJECT_NO_ENTRY_TEMPLATE.render(
            slug=slug,
            description=description,
            dependencies=config["dependencies"],
        )
    (folder / "pyproject.toml").write_text(pyproject)

    # README.md
    readme = README_TEMPLATE.render(
        name=display_name,
        description=description,
        slug=slug,
    )
    (folder / "README.md").write_text(readme)

    # JUSTIFY.md
    justify = JUSTIFY_TEMPLATE.render(
        name=display_name,
        problem=problem,
        existing_solutions="TODO: describe existing solutions",
        proposed_solution=f"{display_name} — {description}",
        impact_criteria="TODO: define success metrics",
        why_now="TODO: explain timing",
    )
    (folder / "JUSTIFY.md").write_text(justify)

    # ARCHITECTURE.md
    arch = ARCHITECTURE_TEMPLATE.render(
        name=display_name,
        overview=f"{display_name} — {description}",
        tech_stack="- Python 3.11+\n- See pyproject.toml for dependencies",
        design_decisions="TODO: key decisions and trade-offs",
        failure_modes="TODO: known failure modes",
    )
    (folder / "ARCHITECTURE.md").write_text(arch)

    # src/{module}/__init__.py
    init_py = INIT_PY_TEMPLATE.render(name=display_name, description=description)
    (pkg_dir / "__init__.py").write_text(init_py)

    # src/{module}/cli.py (if CLI type)
    if config["has_cli"]:
        source_code = CLI_TEMPLATE.render(slug=slug, name=display_name, module=module_name)
        (pkg_dir / "cli.py").write_text(source_code)

    # tests/__init__.py (empty)
    (tests_dir / "__init__.py").write_text("")

    # tests/test_cli.py or tests/test_{module}.py
    if config["has_cli"]:
        test_code = TEST_TEMPLATE.render(slug=slug, module=module_name)
        (tests_dir / "test_cli.py").write_text(test_code)
    else:
        test_code = TEST_TEMPLATE.render(slug=slug, module=module_name)
        (tests_dir / f"test_{module_name}.py").write_text(test_code)

    return folder
