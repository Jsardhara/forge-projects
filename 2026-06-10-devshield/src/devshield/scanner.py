"""Core scanning engine.

Orchestrates dependency extraction, advisory lookup, and result aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from devshield.advisory import AdvisoryClient, AdvisoryResult
from devshield.ai_tooling_db import is_ai_tooling
from devshield.package_managers import Dependency, find_dependencies


@dataclass
class ScanResult:
    """Result of scanning a single package."""
    dependency: Dependency
    is_ai_tooling: bool
    advisory_result: AdvisoryResult | None = None
    skipped: bool = False
    skip_reason: str = ""

    @property
    def is_vulnerable(self) -> bool:
        if self.advisory_result:
            return self.advisory_result.is_vulnerable
        return False

    @property
    def severity(self) -> str:
        if self.advisory_result:
            return self.advisory_result.max_severity
        return "none"


@dataclass
class ScanReport:
    """Full scan report for a project."""
    project_dir: Path
    results: list[ScanResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    scan_time_seconds: float = 0.0

    @property
    def vulnerable_count(self) -> int:
        return sum(1 for r in self.results if r.is_vulnerable)

    @property
    def ai_tooling_count(self) -> int:
        return sum(1 for r in results if r.is_ai_tooling for results in [self.results])

    @property
    def scanned_count(self) -> int:
        return sum(1 for r in self.results if not r.skipped)

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.results if r.skipped)

    @property
    def critical_count(self) -> int:
        return sum(1 for r in self.results if r.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for r in self.results if r.severity == "high")


class Scanner:
    """Main scanner that checks dependencies against the advisory database."""

    def __init__(
        self,
        token: str | None = None,
        scan_all: bool = False,
        max_workers: int = 4,
    ):
        self.token = token
        self.scan_all = scan_all
        self.max_workers = max_workers

    def scan_project(self, project_dir: Path) -> ScanReport:
        """Scan a project directory for vulnerable dependencies."""
        import time
        start = time.monotonic()
        report = ScanReport(project_dir=project_dir)

        deps = find_dependencies(project_dir)
        if not deps:
            report.errors.append("No dependency files found in project directory")
            report.scan_time_seconds = time.monotonic() - start
            return report

        with AdvisoryClient(token=self.token) as client:
            for dep in deps:
                result = self._scan_dependency(dep, client)
                report.results.append(result)

        report.scan_time_seconds = time.monotonic() - start
        return report

    def scan_packages(
        self, packages: list[tuple[str, str]]
    ) -> ScanReport:
        """Scan a list of (name, ecosystem) tuples."""
        import time
        start = time.monotonic()
        report = ScanReport(project_dir=Path("."))

        with AdvisoryClient(token=self.token) as client:
            for name, ecosystem in packages:
                dep = Dependency(name=name, version="unknown", ecosystem=ecosystem)
                result = self._scan_dependency(dep, client)
                report.results.append(result)

        report.scan_time_seconds = time.monotonic() - start
        return report

    def _scan_dependency(
        self, dep: Dependency, client: AdvisoryClient
    ) -> ScanResult:
        """Scan a single dependency."""
        ai = is_ai_tooling(dep.name, dep.ecosystem)

        # Skip non-AI packages unless --all flag
        if not ai and not self.scan_all:
            return ScanResult(
                dependency=dep,
                is_ai_tooling=False,
                skipped=True,
                skip_reason="Not an AI tooling package (use --all to scan all)",
            )

        advisory_result = client.search_by_package(dep.name, dep.ecosystem)

        return ScanResult(
            dependency=dep,
            is_ai_tooling=ai,
            advisory_result=advisory_result,
        )
