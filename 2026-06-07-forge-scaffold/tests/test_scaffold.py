"""Tests for forge_scaffold.scaffold."""

import tempfile
from pathlib import Path

import pytest

from forge_scaffold.scaffold import (
    validate_slug,
    check_duplicate,
    scaffold_project,
    ScaffoldError,
)


class TestValidateSlug:
    def test_valid_slugs(self):
        validate_slug("my-project")
        validate_slug("abc123")
        validate_slug("a-b-c")
        validate_slug("test")

    def test_invalid_slugs(self):
        with pytest.raises(ScaffoldError):
            validate_slug("My-Project")  # uppercase
        with pytest.raises(ScaffoldError):
            validate_slug("my_project")  # underscore
        with pytest.raises(ScaffoldError):
            validate_slug("my--project")  # double hyphen
        with pytest.raises(ScaffoldError):
            validate_slug("")  # empty


class TestCheckDuplicate:
    def test_no_duplicate(self, tmp_path):
        check_duplicate("new-project", tmp_path)  # should not raise

    def test_duplicate_exists(self, tmp_path):
        (tmp_path / "2026-06-07-existing-project").mkdir()
        with pytest.raises(ScaffoldError, match="already exists"):
            check_duplicate("existing-project", tmp_path)


class TestScaffoldProject:
    def test_scaffolds_python_lib(self, tmp_path):
        result = scaffold_project(
            slug="test-lib",
            project_type="python-lib",
            name="Test Lib",
            description="A test library",
            repo_path=tmp_path,
        )
        assert result.exists()
        assert (result / ".gitignore").exists()
        assert (result / "pyproject.toml").exists()
        assert (result / "README.md").exists()
        assert (result / "JUSTIFY.md").exists()
        assert (result / "ARCHITECTURE.md").exists()
        assert (result / "src" / "test_lib" / "__init__.py").exists()
        assert (result / "tests" / "__init__.py").exists()
        assert (result / "tests" / "test_test_lib.py").exists()

    def test_scaffolds_cli_tool(self, tmp_path):
        result = scaffold_project(
            slug="test-cli",
            project_type="cli-tool",
            name="Test CLI",
            description="A test CLI",
            repo_path=tmp_path,
        )
        assert (result / "src" / "test_cli" / "cli.py").exists()
        assert (result / "tests" / "test_cli.py").exists()

    def test_scaffolds_fastapi_service(self, tmp_path):
        result = scaffold_project(
            slug="test-api",
            project_type="fastapi-service",
            name="Test API",
            description="A test API",
            repo_path=tmp_path,
        )
        assert (result / "pyproject.toml").exists()
        content = (result / "pyproject.toml").read_text()
        assert "fastapi" in content

    def test_invalid_type_raises(self, tmp_path):
        with pytest.raises(ScaffoldError, match="Unknown type"):
            scaffold_project(
                slug="test",
                project_type="invalid-type",
                repo_path=tmp_path,
            )

    def test_duplicate_raises(self, tmp_path):
        today = "2026-06-07"
        (tmp_path / f"{today}-dup-project").mkdir()
        with pytest.raises(ScaffoldError):
            scaffold_project(
                slug="dup-project",
                repo_path=tmp_path,
            )

    def test_gitignore_has_required_patterns(self, tmp_path):
        result = scaffold_project(
            slug="test-ignore",
            repo_path=tmp_path,
        )
        gitignore = (result / ".gitignore").read_text()
        assert "__pycache__/" in gitignore
        assert ".venv/" in gitignore
        assert "*.egg-info/" in gitignore
