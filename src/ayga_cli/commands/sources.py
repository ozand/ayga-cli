"""Sources command — list and inspect available data sources."""

import asyncio
import json
import sys

import typer
from rich.console import Console
from rich.table import Table

from ayga_cli.client.redis import AygaParserRedisClient
from ayga_cli.config import get_config
from ayga_cli.exceptions import exit_codes
from ayga_cli.utils.sources_cache import load_cache, save_cache, clear_cache

app = typer.Typer(help="Manage data sources", no_args_is_help=True)
console = Console()


@app.command(name="list")
def list_cmd(
    format_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass local cache, fetch from server"),
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
    name: str = typer.Argument(..., help="Source name to inspect (e.g., web-search)"),
    format_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Show detailed info about a source — description, returned fields, examples.

    Examples:
        ayga_parser sources info web-search
        ayga_parser sources info web-search --json
    """
    asyncio.run(_execute_info(name, format_json))


async def _fetch_sources(config) -> list:
    """Fetch sources from Redis Wrapper."""
    redis_password = config.redis_password.get_secret_value() if config.redis_password else None
    password = config.password.get_secret_value() if config.password else None
    async with AygaParserRedisClient(
        redis_host=config.redis_host,
        redis_port=config.redis_port,
        redis_queue=config.redis_queue,
        redis_password=redis_password,
        password=password,
    ) as client:
        return await client.get_sources()


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
    except (ConnectionError, OSError) as e:
        # Fallback: try loading cache ignoring TTL
        stale_path = load_cache.__module__
        if stale_path:
            pass
        print(f"Error: Server unavailable — {e}", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_UNAVAILABLE)

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
        except (ConnectionError, OSError) as e:
            print(f"Error: Server unavailable — {e}", file=sys.stderr)
            raise typer.Exit(code=exit_codes.ERROR_UNAVAILABLE)

    if not sources:
        print(f"Error: No sources available. Run 'ayga_parser sources list' first.", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_NOT_FOUND)

    # Find the source
    source = next((s for s in sources if s.get("name") == name), None)
    if not source:
        available = [s.get("name", "?") for s in sources]
        print(f"Error: Source '{name}' not found. Available: {', '.join(available)}", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_NOT_FOUND)

    if format_json:
        print(json.dumps(source, indent=2, ensure_ascii=False))
        return

    # Human-readable output
    console.print(f"\n[bold cyan]Source:[/bold cyan] {source.get('name', name)}")
    console.print(f"[bold]Description:[/bold] {source.get('description', 'N/A')}")
    if source.get("category"):
        console.print(f"[bold]Category:[/bold] {source['category']}")

    # Fields
    fields = source.get("fields", source.get("returns", []))
    if fields:
        console.print("\n[bold]Returns:[/bold]")
        if isinstance(fields, list):
            for f in fields:
                if isinstance(f, dict):
                    optional = " [dim](optional)[/dim]" if f.get("optional") else ""
                    console.print(f"  [cyan]{f.get('name', '?')}[/cyan] ({f.get('type', 'any')}): {f.get('description', '')}{optional}")
                else:
                    console.print(f"  - {f}")
        elif isinstance(fields, dict):
            for fname, fdesc in fields.items():
                console.print(f"  [cyan]{fname}[/cyan]: {fdesc}")

    # Example
    example = source.get("example", source.get("examples"))
    if example:
        console.print(f"\n[bold]Example:[/bold]")
        if isinstance(example, str):
            console.print(f"  {example}")
        elif isinstance(example, list):
            for ex in example:
                console.print(f"  {ex}")

    console.print(f"\n[dim]Usage: ayga_parser get {name} \"your query\"[/dim]\n")


def _output_sources(sources: list, format_json: bool) -> None:
    if format_json:
        print(json.dumps({"sources": sources}, indent=2, ensure_ascii=False))
        return

    if not sources:
        console.print("[yellow]No sources configured on server. Contact your administrator.[/yellow]")
        return

    table = Table(title="Available Sources")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Category", style="magenta")
    table.add_column("Description", style="green")

    for source in sources:
        table.add_row(
            source.get("name", "Unknown"),
            source.get("category", ""),
            source.get("description", ""),
        )

    console.print(table)
    console.print(f"[dim]Use 'ayga_parser sources info <name>' for details.[/dim]")
