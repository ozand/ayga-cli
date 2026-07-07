"""Sources command — list and inspect available data sources."""

import asyncio
import json
import sys

import typer
from rich.console import Console
from rich.table import Table

from ayga_cli.client.http import AygaParserHttpClient
from ayga_cli.config import get_config
from ayga_cli.exceptions import AygaParserHTTPError, exit_codes
from ayga_cli.utils.sources_cache import load_cache, save_cache

app = typer.Typer(help="Manage data sources", no_args_is_help=True)
console = Console()


@app.command(name="list")
def list_cmd(
    format_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    no_cache: bool = typer.Option(
        False, "--no-cache", help="Bypass local cache, fetch from server"
    ),
):
    """List available sources from the server.

    Examples:
        ayga_parser sources list
        ayga_parser sources list --json
        ayga_parser sources list --no-cache
    """
    asyncio.run(_execute_list(format_json, no_cache))


@app.command(name="info")
def info_cmd(
    name: str = typer.Argument(..., help="Source name to inspect (e.g., perplexity)"),
    format_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Show detailed info about a source — description, returned fields, examples.

    Examples:
        ayga_parser sources info perplexity
        ayga_parser sources info perplexity --json
    """
    asyncio.run(_execute_info(name, format_json))


def _normalize_source(parser: dict) -> dict:
    """Normalize a Redis Wrapper parser dict into the CLI's source shape.

    Keeps "id" as the primary user-facing name while preserving all other
    fields (including "aparser_name", needed by the 'get' command) and
    setting "name" as an alias for backward-compatible display/lookup.
    """
    normalized = dict(parser)
    normalized.setdefault("name", parser.get("id", parser.get("name", "Unknown")))
    return normalized


async def _fetch_sources(config) -> list:
    """Fetch sources from the Redis Wrapper REST API."""
    async with AygaParserHttpClient(config=config) as client:
        response = await client.list_parsers()
    parsers = response.get("parsers", []) if isinstance(response, dict) else []
    return [_normalize_source(p) for p in parsers]


async def _execute_list(format_json: bool, no_cache: bool) -> None:
    # Try cache first
    if not no_cache:
        cached = load_cache()
        if cached is not None:
            _output_sources(cached, format_json)
            return

    config = get_config()
    try:
        sources = await _fetch_sources(config)
    except (ConnectionError, OSError, AygaParserHTTPError) as e:
        print(f"Error: Server unavailable — {e}", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_UNAVAILABLE) from e

    if sources:
        save_cache(sources)

    _output_sources(sources or [], format_json)


async def _execute_info(name: str, format_json: bool) -> None:
    config = get_config()

    # Try cache first
    cached = load_cache()
    sources = cached

    if not sources:
        try:
            sources = await _fetch_sources(config)
            if sources:
                save_cache(sources)
        except (ConnectionError, OSError, AygaParserHTTPError) as e:
            print(f"Error: Server unavailable — {e}", file=sys.stderr)
            raise typer.Exit(code=exit_codes.ERROR_UNAVAILABLE) from e

    if not sources:
        print(
            "Error: No sources available. Run 'ayga_parser sources list' first.",
            file=sys.stderr,
        )
        raise typer.Exit(code=exit_codes.ERROR_NOT_FOUND)

    # Find the source by id/name; refresh from server on a cache miss before giving up
    source = next((s for s in sources if s.get("id") == name or s.get("name") == name), None)
    if not source and cached is not None:
        try:
            fresh = await _fetch_sources(config)
            if fresh:
                save_cache(fresh)
            sources = fresh
        except (ConnectionError, OSError, AygaParserHTTPError):
            sources = cached
        source = next((s for s in sources if s.get("id") == name or s.get("name") == name), None)

    if not source:
        available = [s.get("id", s.get("name", "?")) for s in sources]
        print(
            f"Error: Source '{name}' not found. Available: {', '.join(available)}",
            file=sys.stderr,
        )
        raise typer.Exit(code=exit_codes.ERROR_NOT_FOUND)

    if format_json:
        print(json.dumps(source, indent=2, ensure_ascii=False))
        return

    # Human-readable output
    console.print(f"\n[bold cyan]Source:[/bold cyan] {source.get('id', source.get('name', name))}")
    console.print(f"[bold]Description:[/bold] {source.get('description', 'N/A')}")
    if source.get("category"):
        console.print(f"[bold]Category:[/bold] {source['category']}")
    if source.get("tags"):
        console.print(f"[bold]Tags:[/bold] {', '.join(source['tags'])}")

    # Fields
    fields = source.get("fields", source.get("returns", []))
    if fields:
        console.print("\n[bold]Returns:[/bold]")
        if isinstance(fields, list):
            for f in fields:
                if isinstance(f, dict):
                    optional = " [dim](optional)[/dim]" if f.get("optional") else ""
                    fname = f.get("name", "?")
                    ftype = f.get("type", "any")
                    fdesc = f.get("description", "")
                    console.print(f"  [cyan]{fname}[/cyan] ({ftype}): {fdesc}{optional}")
                else:
                    console.print(f"  - {f}")
        elif isinstance(fields, dict):
            for fname, fdesc in fields.items():
                console.print(f"  [cyan]{fname}[/cyan]: {fdesc}")

    # Example
    example = source.get("example", source.get("examples"))
    if example:
        console.print("\n[bold]Example:[/bold]")
        if isinstance(example, str):
            console.print(f"  {example}")
        elif isinstance(example, list):
            for ex in example:
                console.print(f"  {ex}")

    display_name = source.get("id", source.get("name", name))
    console.print(f"\n[dim]Usage: ayga_parser get {display_name} \"your query\"[/dim]\n")


def _output_sources(sources: list, format_json: bool) -> None:
    if format_json:
        print(json.dumps({"sources": sources}, indent=2, ensure_ascii=False))
        return

    if not sources:
        console.print(
            "[yellow]No sources configured on server. Contact your administrator.[/yellow]"
        )
        return

    table = Table(title="Available Sources")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Category", style="magenta")
    table.add_column("Description", style="green")

    for source in sources:
        table.add_row(
            source.get("id", source.get("name", "Unknown")),
            source.get("category", ""),
            source.get("description", ""),
        )

    console.print(table)
    console.print("[dim]Use 'ayga_parser sources info <name>' for details.[/dim]")
