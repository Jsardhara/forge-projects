"""Rich CLI for AI Failbook."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from ai_failbook.models import Category, FailureModeCreate, Severity
from ai_failbook.store import Store

console = Console()
DEFAULT_DB = Path(__file__).parent.parent / "failbook.db"


def get_db_path() -> str:
    return str(click.get_current_context().obj.get("db_path", DEFAULT_DB))


def get_store() -> Store:
    return Store(get_db_path())


def print_failure(fm, show_details: bool = False):
    """Pretty-print a failure mode."""
    severity_colors = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
        "critical": "bold red",
    }
    color = severity_colors.get(fm.severity.value, "white")
    verified_badge = " [bold blue]✓ VERIFIED[/]" if fm.verified else ""

    console.print(
        Panel(
            f"[bold]{fm.title}[/]\n\n"
            f"[dim]ID:[/] {fm.vid}  "
            f"[dim]Severity:[/] [{color}]{fm.severity.value.upper()}[/]  "
            f"[dim]Category:[/] {fm.category.value}  "
            f"[dim]Model:[/] {fm.model or 'N/A'}  "
            f"[dim]👍[/] {fm.upvotes}{verified_badge}\n\n"
            + (f"{fm.description}\n\n" if show_details else f"{fm.description[:200]}...\n\n")
            + (f"[dim]Expected:[/] {fm.expected_behavior}\n" if fm.expected_behavior else "")
            + (f"[dim]Actual:[/] {fm.actual_behavior}\n" if fm.actual_behavior else "")
            + (f"[dim]Workaround:[/] {fm.workaround}\n" if fm.workaround else "")
            + (f"[dim]Source:[/] {fm.source_url}\n" if fm.source_url else "")
            + (f"[dim]Tags:[/] {', '.join(fm.tags)}" if fm.tags else ""),
            title=f"[{color}]● {fm.severity.value.upper()}[/]",
            border_style=color,
        )
    )


@click.group()
@click.option("--db", "db_path", default=str(DEFAULT_DB), help="Database path")
@click.pass_context
def cli(ctx, db_path):
    """AI Failbook — Track and learn from AI failure modes."""
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db_path


@cli.command()
@click.option("--q", "query", default=None, help="Search query")
@click.option("--category", type=click.Choice([c.value for c in Category]), default=None)
@click.option("--severity", type=click.Choice([s.value for s in Severity]), default=None)
@click.option("--model", default=None, help="Filter by model name")
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--verified-only", is_flag=True)
@click.option("--limit", default=10, type=int)
@click.option("--json-output", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def search(ctx, query, category, severity, model, tag, verified_only, limit, as_json):
    """Search failure modes."""
    from ai_failbook.models import SearchQuery, Category as Cat, Severity as Sev

    sq = SearchQuery(
        q=query,
        category=Cat(category) if category else None,
        severity=Sev(severity) if severity else None,
        model=model,
        tag=tag,
        verified_only=verified_only,
        limit=limit,
    )
    store = get_store()
    result = store.search(sq)

    if as_json:
        console.print_json(result.model_dump_json())
        return

    if result.total == 0:
        console.print("[yellow]No failure modes found.[/]")
        return

    console.print(f"\n[bold]Found {result.total} failure modes[/]\n")
    for fm in result.items:
        print_failure(fm, show_details=False)


@cli.command()
@click.argument("vid")
@click.option("--json-output", "as_json", is_flag=True)
def show(vid, as_json):
    """Show details of a specific failure mode."""
    store = get_store()
    fm = store.get(vid)
    if fm is None:
        console.print(f"[red]Failure mode {vid} not found[/]")
        sys.exit(1)

    if as_json:
        console.print_json(fm.model_dump_json())
    else:
        print_failure(fm, show_details=True)


@cli.command()
@click.option("--title", prompt=True, help="Short descriptive title")
@click.option("--description", prompt=True, help="Detailed description of the failure")
@click.option("--severity", type=click.Choice([s.value for s in Severity]), default="medium")
@click.option("--category", type=click.Choice([c.value for c in Category]), default="other")
@click.option("--model", default=None, help="AI model that exhibited the failure")
@click.option("--expected", default=None, help="What should have happened")
@click.option("--actual", default=None, help="What actually happened")
@click.option("--workaround", default=None, help="How to avoid or mitigate")
@click.option("--source", default=None, help="Source URL")
@click.option("--tags", default=None, help="Comma-separated tags")
def add(title, description, severity, category, model, expected, actual, workaround, source, tags):
    """Add a new failure mode."""
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    data = FailureModeCreate(
        title=title,
        description=description,
        severity=Severity(severity),
        category=Category(category),
        model=model,
        expected_behavior=expected,
        actual_behavior=actual,
        workaround=workaround,
        source_url=source,
        tags=tag_list,
    )
    store = get_store()
    fm = store.create(data)
    console.print(f"[green]✓ Created failure mode [bold]{fm.vid}[/][/]")
    print_failure(fm, show_details=True)


@cli.command()
@click.argument("vid")
def upvote(vid):
    """Upvote a failure mode (mark it as commonly encountered)."""
    store = get_store()
    fm = store.upvote(vid)
    if fm is None:
        console.print(f"[red]Failure mode {vid} not found[/]")
        sys.exit(1)
    console.print(f"[green]👍 Upvoted![/] {fm.title} — {fm.upvotes} upvotes")


@cli.command()
@click.argument("vid")
@click.confirmation_option(prompt="Are you sure you want to delete this failure mode?")
def delete(vid):
    """Delete a failure mode."""
    store = get_store()
    deleted = store.delete(vid)
    if not deleted:
        console.print(f"[red]Failure mode {vid} not found[/]")
        sys.exit(1)
    console.print(f"[green]✓ Deleted {vid}[/]")


@click.command()
@click.pass_context
def stats(ctx):
    """Show database statistics."""
    store = get_store()
    s = store.stats()

    table = Table(title="AI Failbook Statistics")
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    table.add_row("Total Entries", str(s.total_entries))
    table.add_row("Verified", str(s.verified_count))

    console.print(table)

    if s.by_severity:
        sev_table = Table(title="By Severity")
        sev_table.add_column("Severity")
        sev_table.add_column("Count")
        for sev, count in sorted(s.by_severity.items()):
            sev_table.add_row(sev.upper(), str(count))
        console.print(sev_table)

    if s.by_category:
        cat_table = Table(title="By Category")
        cat_table.add_column("Category")
        cat_table.add_column("Count")
        for cat, count in sorted(s.by_category.items(), key=lambda x: -x[1]):
            cat_table.add_row(cat.replace("_", " ").title(), str(count))
        console.print(cat_table)

    if s.top_tags:
        tag_table = Table(title="Top Tags")
        tag_table.add_column("Tag")
        tag_table.add_column("Count")
        for tag, count in s.top_tags:
            tag_table.add_row(tag, str(count))
        console.print(tag_table)


cli.add_command(stats)


@cli.command()
def seed():
    """Seed the database with sample failure modes."""
    store = get_store()
    existing = store.search(__import__("ai_failbook.models", fromlist=["SearchQuery"]).SearchQuery(limit=1))
    if existing.total > 0:
        console.print("[yellow]Database already has data. Use --db to specify a different database.[/]")
        return
    fms = store.seed_sample_data()
    console.print(f"[green]✓ Seeded {len(fms)} sample failure modes[/]")
    for fm in fms:
        console.print(f"  • [{fm.vid}] {fm.title}")


@cli.command()
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=8100, type=int)
def serve(host, port):
    """Start the REST API server."""
    import uvicorn
    console.print(f"[bold]Starting AI Failbook API on {host}:{port}[/]")
    console.print(f"[dim]Docs: http://{host}:{port}/docs[/]")
    uvicorn.run("ai_failbook.api:app", host=host, port=port, reload=False)


def main():
    cli()


if __name__ == "__main__":
    main()
