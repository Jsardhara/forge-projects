"""CLI collector — fetch MCP servers from GitHub and print or serve."""

from __future__ import annotations

import asyncio
import os
import sys

import click
import structlog

from mcp_tool_scout import GitHubCollector, ScoringEngine, ServerStore, seed_store

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)

logger = structlog.get_logger(__name__)


@click.group()
def cli():
    """MCP Tool Scout - discover and score MCP servers."""
    pass


@cli.command()
@click.option("--token", envvar="GITHUB_TOKEN", default="", help="GitHub token")
@click.option("--min-score", default=0.0, type=float, help="Minimum score filter")
@click.option("--limit", default=20, type=int, help="Max results to show")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def collect(token: str, min_score: float, limit: int, json_output: bool):
    """Collect MCP servers from GitHub and display results."""
    store = ServerStore()

    if token:
        _collect_from_github(store, token)
    else:
        click.echo("No GITHUB_TOKEN - using seed data\n")
        seed_store(store)

    results = store.search(min_score=min_score, sort="score", limit=limit)

    if json_output:
        click.echo(results.model_dump_json(indent=2))
        return

    click.echo(
        f"\nMCP Tool Scout - {results.total} servers found\n"
        f"{'=' * 60}"
    )

    for i, server in enumerate(results.results, 1):
        click.echo(
            f"\n  {i:2}. {server.name}  "
            f"stars:{server.stars:,}  forks:{server.forks:,}  "
            f"Score: {server.score:.1f}"
        )
        click.echo(f"      {server.description[:80]}")
        click.echo(f"      {server.repo_url}")
        if server.topics:
            click.echo(f"      tags: {', '.join(server.topics[:5])}")

    click.echo(f"\n{'=' * 60}")
    click.echo(f"Showing {len(results.results)} of {results.total} servers")


@cli.command()
@click.option("--token", envvar="GITHUB_TOKEN", default="")
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=8765, type=int)
def serve(token: str, host: str, port: int):
    """Start the API server."""
    if token:
        os.environ["GITHUB_TOKEN"] = token

    import uvicorn

    click.echo(f"MCP Tool Scout running at http://{host}:{port}")
    click.echo(f"   API docs: http://{host}:{port}/docs")
    uvicorn.run("mcp_tool_scout.app:app", host=host, port=port, reload=False)


@cli.command()
@click.argument("name")
@click.option("--token", envvar="GITHUB_TOKEN", default="")
def score(name: str, token: str):
    """Score a specific MCP server by name."""
    store = ServerStore()
    if token:
        _collect_from_github(store, token)
    else:
        seed_store(store)

    engine = ScoringEngine()
    found = None
    for s in store.all():
        if name.lower() in s.name.lower():
            found = s
            break

    if not found:
        click.echo(f"Server '{name}' not found. Try 'collect' first.")
        sys.exit(1)

    breakdown = engine.breakdown(found)

    click.echo(f"\nScore Breakdown: {found.name}")
    click.echo(f"{'=' * 45}")
    click.echo(f"  Popularity:      {breakdown.popularity_score:5.1f}/100")
    click.echo(f"  Activity:        {breakdown.activity_score:5.1f}/100")
    click.echo(f"  Documentation:   {breakdown.documentation_score:5.1f}/100")
    click.echo(f"  Freshness:       {breakdown.freshness_score:5.1f}/100")
    click.echo(f"{'=' * 45}")
    click.echo(f"  TOTAL:           {breakdown.total_score:5.1f}/100")
    click.echo(f"\n  {breakdown.recommendation}")


def _collect_from_github(store: ServerStore, token: str) -> None:
    """Async helper to collect from GitHub."""
    collector = GitHubCollector(token=token)

    async def run():
        async for server in collector.collect():
            store.upsert(server)

    asyncio.run(run())


def main():
    cli()


if __name__ == "__main__":
    main()
