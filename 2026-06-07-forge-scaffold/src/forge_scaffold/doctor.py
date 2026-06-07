"""Health checks for the forge-projects repo."""

from pathlib import Path
from typing import List, Tuple

from .repo import scan_projects, git_status

DEFAULT_REPO = Path("C:/Users/jyot2/jarvis/projects/forge-projects-repo")


def check_gitignore(repo_path: Path = DEFAULT_REPO) -> List[Tuple[str, str]]:
    """Check that every project has a .gitignore with required patterns."""
    issues = []
    required_patterns = [".venv/", "__pycache__/", "*.pyc", "*.egg-info/"]

    for item in sorted(repo_path.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue
        parts = item.name.split("-", 3)
        if len(parts) < 4:
            continue

        gitignore = item / ".gitignore"
        if not gitignore.exists():
            issues.append((item.name, "Missing .gitignore"))
            continue

        content = gitignore.read_text()
        for pattern in required_patterns:
            if pattern not in content:
                issues.append((item.name, f".gitignore missing pattern: {pattern}"))

    return issues


def check_test_naming(repo_path: Path = DEFAULT_REPO) -> List[Tuple[str, str]]:
    """Check that test files follow pytest naming conventions."""
    issues = []

    for item in sorted(repo_path.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue
        parts = item.name.split("-", 3)
        if len(parts) < 4:
            continue

        tests_dir = item / "tests"
        if not tests_dir.exists():
            issues.append((item.name, "Missing tests/ directory"))
            continue

        for test_file in tests_dir.iterdir():
            if test_file.name == "__init__.py":
                continue
            if not test_file.name.startswith("test_") and not test_file.name.endswith("_test.py"):
                issues.append((item.name, f"Test file not pytest-discoverable: {test_file.name}"))

    return issues


def check_required_files(repo_path: Path = DEFAULT_REPO) -> List[Tuple[str, str]]:
    """Check that every project has required files."""
    issues = []
    required = ["README.md", "JUSTIFY.md", "ARCHITECTURE.md", "pyproject.toml"]

    for item in sorted(repo_path.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue
        parts = item.name.split("-", 3)
        if len(parts) < 4:
            continue

        for fname in required:
            if not (item / fname).exists():
                issues.append((item.name, f"Missing {fname}"))

    return issues


def run_all_checks(repo_path: Path = DEFAULT_REPO) -> List[Tuple[str, str]]:
    """Run all health checks and return a list of (project, issue) tuples."""
    all_issues = []
    all_issues.extend(check_gitignore(repo_path))
    all_issues.extend(check_required_files(repo_path))
    all_issues.extend(check_test_naming(repo_path))
    return all_issues
