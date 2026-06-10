"""DevShield CLI — AI Coding Supply Chain Security Scanner.

Scans your project's AI tooling dependencies against the GitHub Advisory
Database to detect known vulnerabilities and supply chain attacks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from devshield.config import Config, get_version
from devshield.scanner import Scanner
from devshield.reporters import JsonReporter, TableReporter


@click.group()
@click.version_option(version=get_version(), prog_name="devshield")
def main():
    """DevShield — AI Coding Supply Chain Security Scanner.

    Scans AI tooling dependencies (Claude Code, OpenAI, LangChain, etc.)
    against the GitHub Advisory Database to detect supply chain attacks.
    """
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path), default=Path("."))
@click.option("--all", "scan_all", is_flag=True, help="Scan all packages, not just AI tooling")
@click.option("--json", "output_json", is_flag=True, help="Output JSON (for CI/CD)")
@click.option("--fail-on", type=click.Choice(["low", "medium", "high", "critical"]), default=None,
              help="Fail on severity threshold")
@click.option("--token", envvar="GITHUB_TOKEN", default=None, help="GitHub API token")
def scan(path: Path, scan_all: bool, output_json: bool, fail_on: str | None, token: str | None):
    """Scan a project directory for vulnerable AI tooling dependencies."""
    config = Config.load(path / ".devshield.yaml")

    # CLI flags override config
    if scan_all:
        config.scan_all = True
    if fail_on:
        config.fail_on = fail_on
    if token:
        config.github_token = token

    scanner = Scanner(
        token=config.github_token,
        scan_all=config.scan_all,
    )

    report = scanner.scan_project(path)

    # Output
    if output_json or config.output_format == "json":
        reporter = JsonReporter()
        click.echo(reporter.render(report))
    else:
        reporter = TableReporter()
        reporter.render(report)

    # Exit code
    severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    fail_threshold = severity_order.get(config.fail_on, 3)

    for result in report.results:
        if result.is_vulnerable:
            sev_level = severity_order.get(result.severity, 0)
            if sev_level >= fail_threshold:
                sys.exit(1)

    sys.exit(0)


@main.command()
@click.argument("packages", nargs=-1, required=True)
@click.option("--ecosystem", type=click.Choice(["npm", "pip"]), default="npm",
              help="Package ecosystem")
@click.option("--json", "output_json", is_flag=True, help="Output JSON")
@click.option("--token", envvar="GITHUB_TOKEN", default=None, help="GitHub API token")
def check(packages: tuple[str, ...], ecosystem: str, output_json: bool, token: str | None):
    """Check specific packages for known vulnerabilities.

    Example: devshield check openai anthropic langchain --ecosystem pip
    """
    scanner = Scanner(token=token, scan_all=True)
    pkg_list = [(p, ecosystem) for p in packages]
    report = scanner.scan_packages(pkg_list)

    if output_json:
        reporter = JsonReporter()
        click.echo(reporter.render(report))
    else:
        reporter = TableReporter()
        reporter.render(report)

    if report.vulnerable_count > 0:
        sys.exit(1)
    sys.exit(0)


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path), default=Path("."))
def init(path: Path):
    """Create a .devshield.yaml config file in the project directory."""
    config_path = path / ".devshield.yaml"

    if config_path.exists():
        click.confirm("Config already exists. Overwrite?", abort=True)

    config_content = """# DevShield Configuration
# https://github.com/Jsardhara/forge-projects

# Scan all packages (not just AI tooling)
scan_all: false

# Severity threshold for reporting: low, medium, high, critical
severity_threshold: low

# Output format: table (human-readable) or json (CI/CD)
output_format: table

# Fail CI/CD on this severity or higher: low, medium, high, critical
fail_on: high

# GitHub API token (increases rate limit from 60 to 5000/hr)
# github_token: GITHUB_TOKEN

# Packages to ignore
ignore_packages: []

# Advisory IDs to ignore
ignore_advisories: []
"""
    config_path.write_text(config_content)
    click.echo(f"Created {config_path}")


if __name__ == "__main__":
    main()
