"""CLI interface — npm-shield command."""
import json
import sys
from pathlib import Path

import click

from npm_shield.scanner import scan_lockfile, ScanResult
from npm_shield.report import render_report, render_json
from npm_shield.allowlist import generate_allowlist_json


@click.group()
@click.version_option(version="0.1.0", prog_name="npm-shield")
def main():
    """npm-shield — Audit npm dependencies for install scripts and v12 compliance."""
    pass


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--json-output", is_flag=True, help="Output as JSON instead of rich table.")
@click.option("--lockfile", default="package-lock.json", help="Lockfile name.")
@click.option("--dev", is_flag=True, help="Include dev dependencies in scan.")
def scan(path, json_output, lockfile, dev):
    """Scan a project for npm install scripts.

    PATH is the directory containing the lockfile (default: current directory).
    """
    lockfile_path = Path(path) / lockfile

    try:
        result = scan_lockfile(str(lockfile_path))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if json_output:
        click.echo(render_json(result))
    else:
        render_report(result)


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--lockfile", default="package-lock.json", help="Lockfile name.")
def allowlist(path, lockfile):
    """Generate npm v12 allowlist configuration.

    Outputs the authorization config block to add to your package.json.
    """
    lockfile_path = Path(path) / lockfile

    try:
        result = scan_lockfile(str(lockfile_path))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if not result.packages_affected_by_v12:
        click.echo("No install scripts found. No allowlist needed.")
        sys.exit(0)

    output = generate_allowlist_json(result)
    click.echo(output)


if __name__ == "__main__":
    main()
