"""Configuration loader for .devshield.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

import yaml


@dataclass
class Config:
    """DevShield configuration."""
    scan_all: bool = False
    ignore_packages: list[str] = field(default_factory=list)
    ignore_advisories: list[str] = field(default_factory=list)
    severity_threshold: str = "low"
    output_format: str = "table"
    fail_on: str = "high"
    github_token: str | None = None

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        """Load config from a .devshield.yaml file."""
        if path is None:
            path = Path(".devshield.yaml")

        if not path.exists():
            return cls()

        try:
            data = yaml.safe_load(path.read_text()) or {}
        except (yaml.YAMLError, OSError):
            return cls()

        return cls(
            scan_all=data.get("scan_all", False),
            ignore_packages=data.get("ignore_packages", []),
            ignore_advisories=data.get("ignore_advisories", []),
            severity_threshold=data.get("severity_threshold", "low"),
            output_format=data.get("output_format", "table"),
            fail_on=data.get("fail_on", "high"),
            github_token=data.get("github_token"),
        )


def get_version() -> str:
    """Get the installed devshield version."""
    try:
        return pkg_version("devshield")
    except PackageNotFoundError:
        return "0.1.0-dev"
