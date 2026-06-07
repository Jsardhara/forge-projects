"""Tests for forge_scaffold.doctor."""

import tempfile
from pathlib import Path

import pytest

from forge_scaffold.doctor import (
    check_gitignore,
    check_test_naming,
    check_required_files,
    run_all_checks,
)


@pytest.fixture
def good_project(tmp_path):
    """Create a well-formed project."""
    proj = tmp_path / "2026-06-07-good-project"
    proj.mkdir()
    tests = proj / "tests"
    tests.mkdir()
    (proj / ".gitignore").write_text("__pycache__/\n.venv/\n*.pyc\n*.egg-info/\n")
    (proj / "README.md").write_text("# Test\n\nA project")
    (proj / "JUSTIFY.md").write_text("# Justify")
    (proj / "ARCHITECTURE.md").write_text("# Arch")
    (proj / "pyproject.toml").write_text("[project]\nname='test'")
    (tests / "__init__.py").write_text("")
    (tests / "test_core.py").write_text("# tests")
    return proj


@pytest.fixture
def bad_project(tmp_path):
    """Create a badly-formed project (missing files)."""
    proj = tmp_path / "2026-06-06-bad-project"
    proj.mkdir()
    # No .gitignore, no JUSTIFY.md, no ARCHITECTURE.md
    (proj / "README.md").write_text("# Bad")
    (proj / "pyproject.toml").write_text("[project]\nname='bad'")
    tests = proj / "tests"
    tests.mkdir()
    (tests / "badly_named.py").write_text("# not discoverable")  # bad name
    return proj


class TestCheckGitignore:
    def test_passes_good(self, good_project):
        issues = check_gitignore(good_project.parent)
        assert len(issues) == 0

    def test_flags_missing(self, bad_project):
        issues = check_gitignore(bad_project.parent)
        assert any("Missing .gitignore" in i[1] for i in issues)


class TestCheckTestNaming:
    def test_passes_good(self, good_project):
        issues = check_test_naming(good_project.parent)
        assert len(issues) == 0

    def test_flags_bad_name(self, bad_project):
        issues = check_test_naming(bad_project.parent)
        assert any("not pytest-discoverable" in i[1] for i in issues)


class TestCheckRequiredFiles:
    def test_passes_good(self, good_project):
        issues = check_required_files(good_project.parent)
        assert len(issues) == 0

    def test_flags_missing_justify(self, bad_project):
        issues = check_required_files(bad_project.parent)
        assert any("Missing JUSTIFY.md" in i[1] for i in issues)
        assert any("Missing ARCHITECTURE.md" in i[1] for i in issues)
