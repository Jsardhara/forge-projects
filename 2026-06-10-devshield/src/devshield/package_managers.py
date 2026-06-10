"""Package manager parsers for extracting dependency lists."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Dependency:
    """A single dependency with name and version."""
    name: str
    version: str
    ecosystem: str


class NpmLockParser:
    """Parse package-lock.json to extract dependencies."""

    @staticmethod
    def parse(lockfile: Path) -> list[Dependency]:
        """Extract dependencies from a package-lock.json file."""
        deps: list[Dependency] = []

        if not lockfile.exists():
            return deps

        try:
            data = json.loads(lockfile.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return deps

        # Handle lockfileVersion 2/3
        packages = data.get("packages", {})
        if packages:
            for key, value in packages.items():
                if key == "":
                    continue
                # Strip "node_modules/" prefix
                name = key.replace("node_modules/", "").strip("/")
                version = value.get("version", "unknown")
                if name and version:
                    deps.append(Dependency(name=name, version=version, ecosystem="npm"))
        else:
            # Handle lockfileVersion 1
            dependencies = data.get("dependencies", {})
            for name, info in dependencies.items():
                version = info.get("version", "unknown")
                deps.append(Dependency(name=name, version=version, ecosystem="npm"))

        return deps


class PipRequirementsParser:
    """Parse requirements.txt to extract dependencies."""

    # Match lines like: package==1.0.0, package>=1.0, package~=1.0, package
    PATTERN = re.compile(
        r"^([a-zA-Z0-9_-]+)\s*(?:==|>=|<=|~=|!=|<|>)?\s*([a-zA-Z0-9._-]+)?"
    )

    @classmethod
    def parse(cls, req_file: Path) -> list[Dependency]:
        """Extract dependencies from a requirements.txt file."""
        deps: list[Dependency] = []

        if not req_file.exists():
            return deps

        try:
            lines = req_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return deps

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # Handle extras: package[extra]==1.0 -> package
            clean = re.sub(r"\[.*\]", "", line)
            match = cls.PATTERN.match(clean)
            if match:
                name = match.group(1)
                version = match.group(2) or "unknown"
                deps.append(Dependency(name=name, version=version, ecosystem="pip"))

        return deps


class PyprojectParser:
    """Parse pyproject.toml for dependencies."""

    @staticmethod
    def parse(pyproject: Path) -> list[Dependency]:
        """Extract dependencies from pyproject.toml (basic TOML parsing)."""
        deps: list[Dependency] = []

        if not pyproject.exists():
            return deps

        try:
            content = pyproject.read_text(encoding="utf-8")
        except OSError:
            return deps

        # Simple regex-based extraction for dependencies array
        # Works for standard pyproject.toml without full TOML parser
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("[project]") or stripped.startswith("[tool.poetry.deps]"):
                continue
            if "dependencies" in stripped and "=" in stripped and "[" in stripped:
                in_deps = True
                continue
            if in_deps:
                if stripped == "]":
                    in_deps = False
                    continue
                # Extract "package>=1.0.0" or "package"
                match = re.match(r'"([^"]+)"', stripped.rstrip(","))
                if match:
                    dep_str = match.group(1)
                    # Split on version specifiers
                    parts = re.split(r"[><=!~]", dep_str, maxsplit=1)
                    name = parts[0].strip()
                    version = parts[1].strip() if len(parts) > 1 else "unknown"
                    if name:
                        deps.append(Dependency(name=name, version=version, ecosystem="pip"))

        return deps


def find_dependencies(project_dir: Path) -> list[Dependency]:
    """Auto-detect and parse all dependency files in a project directory."""
    all_deps: list[Dependency] = []

    # npm
    lockfile = project_dir / "package-lock.json"
    if lockfile.exists():
        all_deps.extend(NpmLockParser.parse(lockfile))

    # pip requirements
    for req_name in ("requirements.txt", "requirements-dev.txt", "requirements-prod.txt"):
        req_file = project_dir / req_name
        if req_file.exists():
            all_deps.extend(PipRequirementsParser.parse(req_file))

    # pyproject.toml
    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        all_deps.extend(PyprojectParser.parse(pyproject))

    return all_deps
