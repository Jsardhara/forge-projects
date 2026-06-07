"""CLI entry point for forge-scaffold."""

import datetime
import subprocess
import sys
from pathlib import Path

import click

from .scaffold import scaffold_project, ScaffoldError, PROJECT_TYPES
from .repo import (
    scan_projects,
    update_index,
    git_commit_all,
    git_push,
    git_status,
    get_project_count,
    get_last_project,
)
from .doctor import run_all_checks
from .bus_integration import publish_code_ready

DEFAULT_REPO = Path("C:/Users/jyot2/jarvis/projects/forge-projects-repo")


@click.group()
@click.option("--repo", default=None, help="Path to forge-projects repo")
@click.pass_context
def main(ctx, repo):
    """forge-scaffold — Automate the Forge daily build scaffolding workflow."""
    ctx.ensure_object(dict)
    ctx.obj["repo"] = Path(repo) if repo else DEFAULT_REPO


@main.command()
@click.argument("slug")
@click.option(
    "--type", "project_type",
    default="python-lib",
    type=click.Choice(PROJECT_TYPES.keys()),
    help="Project type",
)
@click.option("--name", default=None, help="Display name (default: slug as title)")
@click.option("--description", default="A new Forge project", help="Short description")
@click.option("--problem", default="TODO: describe the problem", help="Problem statement")
@click.option("--push", is_flag=True, help="Commit and push after scaffolding")
@click.pass_context
def new(ctx, slug, project_type, name, description, problem, push):
    """Scaffold a new project in the forge-projects repo."""
    repo = ctx.obj["repo"]

    click.echo(f"Scaffolding '{slug}' ({project_type})...")

    try:
        project_dir = scaffold_project(
            slug=slug,
            project_type=project_type,
            name=name,
            description=description,
            problem=problem,
            repo_path=repo,
            push=push,
        )
    except ScaffoldError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"  Created: {project_dir}")
    click.echo(f"  Files:")
    for f in sorted(project_dir.rglob("*")):
        if f.is_file():
            rel = f.relative_to(project_dir)
            click.echo(f"    {rel}")

    # Install and test
    click.echo("\nInstalling...")
    venv_python = Path(
        "C:/Users/jyot2/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"
    )
    if venv_python.exists():
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-e", f"{project_dir}[dev]"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            click.echo(f"  Install warning: {result.stderr[-200:]}", err=True)
        else:
            click.echo("  Install OK")

        click.echo("Running tests...")
        result = subprocess.run(
            [str(venv_python), "-m", "pytest", str(project_dir / "tests"), "-v"],
            capture_output=True,
            text=True,
        )
        click.echo(result.stdout)
        if result.returncode != 0:
            click.echo(f"  Test output: {result.stderr[-300:]}", err=True)
    else:
        click.echo("  Skipping install/test (venv python not found)")

    # Update INDEX.md
    click.echo("Updating INDEX.md...")
    update_index(repo)
    click.echo("  INDEX.md updated")

    # Git commit
    today = datetime.date.today().isoformat()
    if push:
        click.echo("Committing and pushing...")
        git_commit_all(f"feat: {slug} -- scaffolded {project_type} ({today})", repo)
        if git_push(repo):
            click.echo("  Pushed to origin/main")
        else:
            click.echo("  Push failed — push manually", err=True)
    else:
        click.echo("  (use --push to auto-commit and push)")

    # Publish to bus
    publish_code_ready(slug, "scaffolded", str(project_dir))

    click.echo(f"\nDone! Project: {project_dir}")


@main.command()
@click.pass_context
def doctor(ctx):
    """Check the forge-projects repo for common issues."""
    repo = ctx.obj["repo"]
    click.echo(f"Checking repo: {repo}\n")

    issues = run_all_checks(repo)

    if not issues:
        click.echo("All checks passed!")
    else:
        click.echo(f"Found {len(issues)} issue(s):\n")
        for project, issue in issues:
            click.echo(f"  [{project}] {issue}")
        sys.exit(1)


@main.command()
@click.pass_context
def index(ctx):
    """Rebuild INDEX.md from scratch by scanning the repo."""
    repo = ctx.obj["repo"]
    content = update_index(repo)
    projects = scan_projects(repo)
    click.echo(f"Rebuilt INDEX.md with {len(projects)} projects")


@main.command()
@click.pass_context
def status(ctx):
    """Show repo state."""
    repo = ctx.obj["repo"]
    count = get_project_count(repo)
    last = get_last_project(repo)
    status_out = git_status(repo)

    click.echo(f"Repo: {repo}")
    click.echo(f"Projects: {count}")
    if last:
        click.echo(f"Last project: {last['folder']} ({last['date']})")
    if status_out:
        click.echo(f"\nUncommitted changes:\n{status_out}")
    else:
        click.echo("Working tree clean")


if __name__ == "__main__":
    main()
