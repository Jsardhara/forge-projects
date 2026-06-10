"""Tests for package manager parsers."""

import json
import tempfile
from pathlib import Path

from devshield.package_managers import (
    NpmLockParser,
    PipRequirementsParser,
    PyprojectParser,
    find_dependencies,
)


def test_npm_lock_parser_v2():
    lock_data = {
        "name": "test-project",
        "lockfileVersion": 2,
        "packages": {
            "": {"name": "test-project"},
            "node_modules/openai": {"version": "4.20.0", "resolved": "https://registry.npmjs.org/openai/-/openai-4.20.0.tgz"},
            "node_modules/@anthropic-ai/claude-code": {"version": "0.1.0", "resolved": "https://registry.npmjs.org/@anthropic-ai/claude-code/-/claude-code-0.1.0.tgz"},
            "node_modules/express": {"version": "4.18.0"},
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(lock_data, f)
        f.flush()
        deps = NpmLockParser.parse(Path(f.name))

    assert len(deps) == 3
    names = {d.name for d in deps}
    assert "openai" in names
    assert "@anthropic-ai/claude-code" in names

    Path(f.name).unlink()


def test_npm_lock_parser_v1():
    lock_data = {
        "name": "test-project",
        "lockfileVersion": 1,
        "dependencies": {
            "openai": {"version": "4.20.0"},
            "express": {"version": "4.18.0"},
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(lock_data, f)
        f.flush()
        deps = NpmLockParser.parse(Path(f.name))

    assert len(deps) == 2
    names = {d.name for d in deps}
    assert "openai" in names

    Path(f.name).unlink()


def test_npm_lock_parser_missing_file():
    deps = NpmLockParser.parse(Path("/nonexistent/package-lock.json"))
    assert deps == []


def test_npm_lock_parser_invalid_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json{{{")
        f.flush()
        deps = NpmLockParser.parse(Path(f.name))

    assert deps == []
    Path(f.name).unlink()


def test_pip_requirements_parser():
    content = """# Project dependencies
openai==1.2.3
anthropic>=0.5.0
langchain~=0.1.0
# Dev deps
pytest>=7.0
flask  # web framework
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        deps = PipRequirementsParser.parse(Path(f.name))

    assert len(deps) >= 4
    names = {d.name for d in deps}
    assert "openai" in names
    assert "anthropic" in names
    assert "langchain" in names

    Path(f.name).unlink()


def test_pip_requirements_parser_missing_file():
    deps = PipRequirementsParser.parse(Path("/nonexistent/requirements.txt"))
    assert deps == []


def test_pyproject_parser():
    content = '''[project]
name = "myproject"
version = "0.1.0"
dependencies = [
    "openai>=1.0.0",
    "anthropic>=0.5.0",
    "flask",
]
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(content)
        f.flush()
        deps = PyprojectParser.parse(Path(f.name))

    assert len(deps) >= 2
    names = {d.name for d in deps}
    assert "openai" in names
    assert "anthropic" in names

    Path(f.name).unlink()


def test_pyproject_parser_missing_file():
    deps = PyprojectParser.parse(Path("/nonexistent/pyproject.toml"))
    assert deps == []


def test_find_dependencies_no_files(tmp_path):
    deps = find_dependencies(tmp_path)
    assert deps == []
