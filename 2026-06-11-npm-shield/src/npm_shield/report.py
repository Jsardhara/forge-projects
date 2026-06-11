"""Rich-formatted report output for scan results."""
from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from npm_shield.scanner import ScanResult, PackageScriptInfo, classify_risk


def _risk_style(risk: str) -> str:
    """Return Rich style string for a risk level."""
    return {
        "HIGH": "bold red",
        "MEDIUM": "yellow",
        "LOW": "dim green",
    }.get(risk, "white")


def render_report(scan_result: ScanResult, console: Console = None) -> None:
    """Render a full Rich-formatted report of scan results."""
    if console is None:
        console = Console()

    # Header
    header_text = Text()
    header_text.append("npm-shield", style="bold cyan")
    header_text.append(" — npm v12 Migration Scanner", style="white")
    console.print()
    console.print(header_text)
    console.print(f"Project: {scan_result.project_name} v{scan_result.project_version}")
    console.print(f"Lockfile version: {scan_result.lockfile_version}")
    console.print()

    # Summary
    affected = scan_result.packages_affected_by_v12
    total_with_scripts = len(scan_result.packages_with_scripts)

    summary_parts = [
        f"Total packages: {scan_result.total_packages}",
        f"Packages with any scripts: {total_with_scripts}",
        f"Packages affected by npm v12 (install scripts): {len(affected)}",
    ]
    console.print(Panel("\n".join(summary_parts), title="Summary", border_style="cyan"))
    console.print()

    if not affected:
        console.print("[bold green]No install scripts found![/bold green] "
                      "Your project is npm v12 ready.")
        return

    # Risk breakdown
    high = [p for p in affected if classify_risk(p) == "HIGH"]
    medium = [p for p in affected if classify_risk(p) == "MEDIUM"]
    low = [p for p in affected if classify_risk(p) == "LOW"]

    risk_table = Table(title="Risk Breakdown", show_header=True, header_style="bold")
    risk_table.add_column("Risk", style="bold", width=10)
    risk_table.add_column("Count", justify="right")
    risk_table.add_column("Action Required")

    risk_table.add_row(
        Text("HIGH", style="bold red"),
        str(len(high)),
        "Multiple install scripts — requires immediate review"
    )
    risk_table.add_row(
        Text("MEDIUM", style="yellow"),
        str(len(medium)),
        "Single install script — verify necessity"
    )
    risk_table.add_row(
        Text("LOW", style="dim green"),
        str(len(low)),
        "Publish-only scripts — no action needed"
    )
    console.print(risk_table)
    console.print()

    # Detailed findings table
    detail_table = Table(title="Install Script Findings", show_header=True, header_style="bold")
    detail_table.add_column("Package", style="bold", max_width=35)
    detail_table.add_column("Version", max_width=15)
    detail_table.add_column("Scripts", max_width=40)
    detail_table.add_column("Risk", width=8)

    for pkg in affected:
        risk = classify_risk(pkg)
        scripts_str = ", ".join(sorted(pkg.scripts.keys()))
        detail_table.add_row(
            pkg.name,
            pkg.version,
            scripts_str,
            Text(risk, style=_risk_style(risk)),
        )

    console.print(detail_table)
    console.print()

    # Recommendations
    console.print("[bold]Next Steps:[/bold]")
    console.print("1. Review each package above — is the install script necessary?")
    console.print("2. Run [bold cyan]npm-shield allowlist[/bold cyan] to generate v12 config")
    console.print("3. Add the generated config to your package.json")
    console.print("4. Test with [bold cyan]npm --version 12[/bold cyan] (when available)")
    console.print()


def render_json(scan_result: ScanResult) -> str:
    """Render scan results as JSON string."""
    import json
    from dataclasses import asdict

    data = {
        "project": {
            "name": scan_result.project_name,
            "version": scan_result.project_version,
        },
        "lockfile_version": scan_result.lockfile_version,
        "total_packages": scan_result.total_packages,
        "packages_with_scripts": [
            {
                **asdict(pkg),
                "risk": classify_risk(pkg),
            }
            for pkg in scan_result.packages_with_scripts
        ],
        "packages_affected_by_v12": [
            pkg.name for pkg in scan_result.packages_affected_by_v12
        ],
        "scan_path": scan_result.scan_path,
    }
    return json.dumps(data, indent=2)
