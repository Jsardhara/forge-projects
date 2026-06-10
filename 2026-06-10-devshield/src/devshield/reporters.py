"""Output reporters for scan results."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text

from devshield.scanner import ScanReport, ScanResult


def _severity_style(severity: str) -> str:
    """Get Rich style for a severity level."""
    return {
        "critical": "bold white on red",
        "high": "bold red",
        "medium": "bold yellow",
        "low": "bold blue",
        "none": "green",
        "unknown": "dim",
    }.get(severity, "dim")


class TableReporter:
    """Rich terminal table output."""

    def __init__(self):
        self.console = Console()

    def render(self, report: ScanReport) -> None:
        """Render a scan report as a rich table."""
        # Summary header
        self.console.print()
        self.console.print(
            f"[bold]DevShield Scan Report[/bold] — {report.project_dir}"
        )
        self.console.print(
            f"Scanned: {report.scanned_count} | "
            f"Skipped: {report.skipped_count} | "
            f"Vulnerable: [bold red]{report.vulnerable_count}[/bold red] | "
            f"Critical: [bold white on red]{report.critical_count}[/bold white on red] | "
            f"High: [bold red]{report.high_count}[/bold red] | "
            f"Time: {report.scan_time_seconds:.1f}s"
        )
        self.console.print()

        if not report.results:
            self.console.print("[yellow]No packages found to scan.[/yellow]")
            return

        # Results table
        table = Table(title="Scan Results", show_lines=False)
        table.add_column("Package", style="cyan", no_wrap=True)
        table.add_column("Eco", style="dim", width=5)
        table.add_column("Version", style="dim")
        table.add_column("AI Tooling", width=10)
        table.add_column("Status", width=10)
        table.add_column("Severity", width=10)
        table.add_column("Advisories", width=5)
        table.add_column("Details", max_width=50)

        for result in report.results:
            if result.skipped:
                table.add_row(
                    result.dependency.name,
                    result.dependency.ecosystem,
                    result.dependency.version,
                    "—",
                    "[dim]skipped[/dim]",
                    "—",
                    "—",
                    result.skip_reason,
                )
                continue

            severity = result.severity
            style = _severity_style(severity)
            adv_count = (
                len(result.advisory_result.advisories)
                if result.advisory_result
                else 0
            )

            # Get top advisory summary
            details = ""
            if result.advisory_result and result.advisory_result.advisories:
                top = result.advisory_result.advisories[0]
                details = f"[{top.ghsa_id}] {top.summary[:60]}"

            table.add_row(
                result.dependency.name,
                result.dependency.ecosystem,
                result.dependency.version,
                "[bold magenta]YES[/bold magenta]" if result.is_ai_tooling else "no",
                f"[{style}]⚠ VULN[/{style}]" if result.is_vulnerable else "[green]✓ clean[/green]",
                f"[{style}]{severity.upper()}[/{style}]",
                str(adv_count) if adv_count > 0 else "0",
                details,
            )

        self.console.print(table)

        # Error summary
        if report.errors:
            self.console.print()
            for err in report.errors:
                self.console.print(f"[yellow]⚠ {err}[/yellow]")

        # Exit code hint
        self.console.print()
        if report.vulnerable_count > 0:
            self.console.print(
                f"[bold red]FAIL[/bold red] — {report.vulnerable_count} vulnerable package(s) found"
            )
        else:
            self.console.print("[bold green]PASS[/bold green] — No known vulnerabilities found")


class JsonReporter:
    """JSON output for CI/CD integration."""

    def render(self, report: ScanReport) -> str:
        """Render a scan report as JSON."""
        output = {
            "project_dir": str(report.project_dir),
            "scan_time_seconds": report.scan_time_seconds,
            "summary": {
                "total_packages": len(report.results),
                "scanned": report.scanned_count,
                "skipped": report.skipped_count,
                "vulnerable": report.vulnerable_count,
                "critical": report.critical_count,
                "high": report.high_count,
                "pass": report.vulnerable_count == 0,
            },
            "results": [],
            "errors": report.errors,
        }

        for result in report.results:
            entry = {
                "package": result.dependency.name,
                "ecosystem": result.dependency.ecosystem,
                "version": result.dependency.version,
                "is_ai_tooling": result.is_ai_tooling,
                "skipped": result.skipped,
                "severity": result.severity,
                "vulnerable": result.is_vulnerable,
            }
            if result.advisory_result:
                entry["advisories"] = [
                    {
                        "ghsa_id": a.ghsa_id,
                        "cve_id": a.cve_id,
                        "summary": a.summary,
                        "severity": a.severity,
                        "url": a.url,
                    }
                    for a in result.advisory_result.advisories
                ]
                entry["error"] = result.advisory_result.error
            output["results"].append(entry)

        return json.dumps(output, indent=2)
