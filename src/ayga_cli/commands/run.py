"""Run command for executing ayga_parser with dry-run and pagination support."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

import typer
from rich.console import Console
from rich.json import JSON as RichJSON
from rich.panel import Panel
from rich.table import Table

from ayga_cli.client.http import AygaParserHttpClient
from ayga_cli.config import get_config
from ayga_cli.presets import get_preset_manager
from ayga_cli.static_manifest import (
    get_parser_defaults,
    get_default_overrides,
    get_required_overrides,
    validate_overrides,
    get_parser_examples,
    format_example,
)
from ayga_cli.utils.dry_run import DryRunSimulator
from ayga_cli.utils.pagination import execute_with_pagination
from ayga_cli.proxy_strategy import merge_with_proxy

app = typer.Typer(
    help="Execute ayga_parser requests",
    no_args_is_help=True,
)
console = Console()


def parse_options(options_str: Optional[str]) -> list[dict]:
    """Parse options string into list of option dicts.

    Args:
        options_str: Comma-separated key=value pairs or JSON array

    Returns:
        List of option dictionaries

    Examples:
        >>> parse_options("depth=5,timeout=30")
        [{"id": "depth", "value": 5}, {"id": "timeout", "value": 30}]
    """
    if not options_str:
        return []

    options = []

    # Try JSON first
    try:
        data = json.loads(options_str)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [{"id": k, "value": v} for k, v in data.items()]
    except json.JSONDecodeError:
        pass

    # Parse key=value pairs
    for pair in options_str.split(","):
        pair = pair.strip()
        if "=" in pair:
            key, value = pair.split("=", 1)
            key = key.strip()
            value = value.strip()

            # Try to convert value to appropriate type
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    # Keep as string, but handle booleans
                    if value.lower() == "true":
                        value = True
                    elif value.lower() == "false":
                        value = False

            options.append({"id": key, "value": value})

    return options


def merge_options(
    user_options: list[dict],
    default_overrides: dict[str, Any],
) -> list[dict]:
    """Merge user options with default overrides.

    User options take precedence over defaults.

    Args:
        user_options: Options provided by user
        default_overrides: Default overrides from static manifest

    Returns:
        Merged list of options
    """
    # Convert user options to dict for easy lookup
    user_dict = {opt["id"]: opt["value"] for opt in user_options}

    # Merge defaults (user options take precedence)
    merged = {**default_overrides, **user_dict}

    # Convert back to list format
    return [{"id": k, "value": v} for k, v in merged.items()]


@app.command()
def run(
    parser: Optional[str] = typer.Argument(None, help="Parser name (e.g., SE::Google) - optional if using --saved-preset"),
    query: Optional[str] = typer.Argument(None, help="Query string to parse"),
    preset_name: str = typer.Option("default", "--preset", "-p", help="Parser preset name"),
    saved_preset: Optional[str] = typer.Option(
        None,
        "--saved-preset",
        "-s",
        help="Use saved preset (name from 'ayga_parser presets list')",
    ),
    options: Optional[str] = typer.Option(
        None,
        "--options",
        "-o",
        help="Options as key=value pairs or JSON (e.g., 'depth=5,pagecount=3')",
    ),
    examples: bool = typer.Option(
        False,
        "--examples",
        "-e",
        help="Show usage examples for this parser and exit",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Preview execution without making API call",
    ),
    page_all: bool = typer.Option(
        False,
        "--page-all",
        "-a",
        help="Auto-fetch all pages of results",
    ),
    max_pages: int = typer.Option(
        10,
        "--max-pages",
        "-m",
        help="Maximum pages to fetch with --page-all",
    ),
    transport: str = typer.Option(
        "http",
        "--transport",
        "-t",
        help="Transport method: http or redis",
    ),
    format_json: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output as JSON",
    ),
    timeout: int = typer.Option(
        300,
        "--timeout",
        help="Request timeout in seconds",
    ),
    async_mode: bool = typer.Option(
        False,
        "--async",
        help="Use async Redis mode (returns immediately with task ID)",
    ),
):
    """Execute a parser request with optional dry-run and pagination.

    Examples:
        # Basic execution
        ayga_parser run SE::Google "machine learning"

        # Use saved preset
        ayga_parser run "What is AI?" --saved-preset perplexity-business

        # Dry-run to preview
        ayga_parser run SE::Google "test" --dry-run

        # With options
        ayga_parser run SE::Google "test" --options "pagecount=5,region=us"

        # Show examples
        ayga_parser run FreeAI::Perplexity --examples

        # Auto-pagination
        ayga_parser run SE::Google "test" --page-all --max-pages 20

        # JSON output
        ayga_parser run SE::Google "test" --json
    """
    config = get_config()

    # Handle --examples flag first (doesn't require query)
    if examples:
        if not parser:
            if format_json:
                console.print(json.dumps({
                    "status": "error",
                    "error": "Parser name is required for --examples",
                }, indent=2))
            else:
                console.print("[red]Error:[/red] Parser name is required for --examples")
            raise typer.Exit(code=1)
        _show_examples(parser, format_json)
        raise typer.Exit()

    # Validate query is provided
    if not query:
        if format_json:
            console.print(json.dumps({
                "status": "error",
                "error": "Query is required",
            }, indent=2))
        else:
            console.print("[red]Error:[/red] Query is required")
        raise typer.Exit(code=1)

    # Handle saved preset
    if saved_preset:
        preset_manager = get_preset_manager()
        preset = preset_manager.get_preset(saved_preset)
        if not preset:
            error_msg = f"Saved preset '{saved_preset}' not found"
            if format_json:
                console.print(json.dumps({
                    "status": "error",
                    "error": error_msg,
                }, indent=2))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
                console.print("Use [cyan]ayga_parser presets list[/cyan] to see available presets.")
            raise typer.Exit(code=1)
        parser = preset.parser
        # Start with preset overrides
        base_overrides = dict(preset.overrides)
    else:
        if not parser:
            if format_json:
                console.print(json.dumps({
                    "status": "error",
                    "error": "Parser name is required (or use --saved-preset)",
                }, indent=2))
            else:
                console.print("[red]Error:[/red] Parser name is required (or use --saved-preset)")
            raise typer.Exit(code=1)
        base_overrides = {}

    # Parse user options
    user_options = parse_options(options)

    # Merge: preset overrides < default overrides < user options
    # First apply preset overrides as base
    merged_overrides = dict(base_overrides)

    # Get default overrides for known parsers
    default_overrides = get_default_overrides(parser)
    if default_overrides:
        # Defaults fill in what's not already set
        for key, value in default_overrides.items():
            if key not in merged_overrides:
                merged_overrides[key] = value

    # User options take highest precedence
    user_dict = {opt["id"]: opt["value"] for opt in user_options}
    merged_overrides.update(user_dict)

    # Convert back to list format
    user_options = [{"id": k, "value": v} for k, v in merged_overrides.items()]

    if transport in ('http', 'redis'):
        user_options = merge_with_proxy(parser, user_options)

    # Validate required overrides
    is_valid, missing = validate_overrides(
        parser, {opt["id"]: opt["value"] for opt in user_options}
    )
    if not is_valid:
        error_msg = f"Missing required overrides: {', '.join(missing)}"
        if format_json:
            console.print(json.dumps({
                "status": "error",
                "error": error_msg,
                "missing_overrides": missing,
            }, indent=2))
        else:
            console.print(f"[red]Error:[/red] {error_msg}")
            console.print(f"\n[yellow]Tip:[/yellow] Use [cyan]ayga_parser run {parser} --examples[/cyan] to see usage examples")
        raise typer.Exit(code=1)

    # Handle dry-run mode
    if dry_run:
        simulator = DryRunSimulator(
            parser=parser,
            query=query,
            preset=preset_name,
            options=user_options,
            transport=transport,
            config=config,
        )

        if format_json:
            preview = simulator.generate_preview()
            console.print(json.dumps(preview, indent=2, ensure_ascii=False))
        else:
            simulator.print_preview()

        raise typer.Exit()

    # Execute based on mode
    try:
        if page_all:
            # Async pagination mode
            result = asyncio.run(_execute_paginated(
                parser=parser,
                query=query,
                preset=preset_name,
                options=user_options,
                max_pages=max_pages,
                timeout=timeout,
            ))
        else:
            # Single request mode
            result = asyncio.run(_execute_single(
                parser=parser,
                query=query,
                preset=preset_name,
                options=user_options,
                timeout=timeout,
            ))

        # Output results
        if format_json:
            console.print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            _print_results(result, page_all)

    except Exception as e:
        if format_json:
            console.print(json.dumps({
                "status": "error",
                "error": str(e),
            }, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


def _show_examples(parser: str, format_json: bool) -> None:
    """Show usage examples for a parser."""
    defaults = get_parser_defaults(parser)

    if not defaults:
        if format_json:
            console.print(json.dumps({
                "status": "error",
                "message": f"No examples found for parser '{parser}'",
                "available_parsers": list(get_parser_defaults.__wrapped__.__module__ if hasattr(get_parser_defaults, '__wrapped__') else []),
            }, indent=2))
        else:
            console.print(f"[yellow]No examples found for parser '{parser}'[/yellow]")
            console.print("\n[dim]This parser is not in the static manifest.[/dim]")
            console.print("[dim]You can still use it with standard options.[/dim]")
        return

    if format_json:
        data = {
            "parser": parser,
            "description": defaults.description,
            "category": defaults.category,
            "required_overrides": defaults.required_overrides,
            "default_overrides": defaults.default_overrides,
            "notes": defaults.notes,
            "examples": [
                {
                    "description": ex.get("desc", ""),
                    "command": format_example(parser, ex),
                }
                for ex in defaults.examples
            ],
        }
        console.print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        # Display in rich format
        console.print(Panel.fit(
            f"[bold cyan]{parser}[/bold cyan]\n"
            f"[dim]{defaults.description}[/dim]",
            border_style="cyan"
        ))

        # Show required overrides
        if defaults.required_overrides:
            console.print(f"\n[bold yellow]Required Overrides:[/bold yellow]")
            for req in defaults.required_overrides:
                console.print(f"  • [red]{req}[/red]")

        # Show default overrides
        if defaults.default_overrides:
            console.print(f"\n[bold green]Default Overrides:[/bold green]")
            for key, value in defaults.default_overrides.items():
                console.print(f"  • {key} = [cyan]{value}[/cyan]")

        # Show notes
        if defaults.notes:
            console.print(f"\n[bold blue]Note:[/bold blue] {defaults.notes}")

        # Show examples
        if defaults.examples:
            console.print(f"\n[bold]Examples:[/bold]")
            for i, ex in enumerate(defaults.examples, 1):
                desc = ex.get("desc", "")
                cmd = format_example(parser, ex)
                console.print(f"\n  [dim]{i}. {desc}[/dim]")
                console.print(f"     [green]$[/green] [white]{cmd}[/white]")

        console.print()


async def _execute_single(
    parser: str,
    query: str,
    preset: str,
    options: list[dict],
    timeout: int,
) -> dict[str, Any]:
    """Execute single parser request."""
    config = get_config()

    async with AygaParserHttpClient(config, timeout=timeout) as client:
        result = await client.one_request(
            parser=parser,
            query=query,
            preset=preset,
            options=options,
        )
        return result


async def _execute_paginated(
    parser: str,
    query: str,
    preset: str,
    options: list[dict],
    max_pages: int,
    timeout: int,
) -> dict[str, Any]:
    """Execute parser with pagination."""
    config = get_config()

    async def execute_fn(**kwargs) -> dict:
        async with AygaParserHttpClient(config, timeout=timeout) as client:
            return await client.one_request(**kwargs)

    return await execute_with_pagination(
        execute_fn=execute_fn,
        parser=parser,
        query=query,
        base_options=options,
        max_pages=max_pages,
        preset=preset,
        show_progress=True,
    )


def _print_results(result: dict[str, Any], is_paginated: bool = False) -> None:
    """Print results in human-readable format."""
    # Handle paginated results
    if is_paginated:
        pages_fetched = result.get("pages_fetched", 1)
        total_items = result.get("total_items", 0)
        results = result.get("results", [])

        console.print(Panel.fit(
            f"[bold green]Results collected[/bold green]\n"
            f"Pages: {pages_fetched} | Items: {total_items}",
            border_style="green"
        ))

        if results:
            table = Table(title="Results")

            # Determine columns from first result
            if isinstance(results[0], dict):
                for key in results[0].keys():
                    table.add_column(str(key))

                for item in results[:20]:  # Limit display
                    row = [str(v) for v in item.values()]
                    table.add_row(*row)

                if len(results) > 20:
                    table.add_row(f"... and {len(results) - 20} more items")

                console.print(table)
            else:
                for i, item in enumerate(results[:20]):
                    console.print(f"{i+1}. {item}")
                if len(results) > 20:
                    console.print(f"... and {len(results) - 20} more items")
        else:
            console.print("[yellow]No results found[/yellow]")

    else:
        # Single request results
        data = result.get("data", {})
        results = data.get("results", [])

        if results:
            console.print(Panel.fit(
                f"[bold green]Success[/bold green] | Items: {len(results)}",
                border_style="green"
            ))

            table = Table(title="Results")

            if isinstance(results[0], dict):
                for key in results[0].keys():
                    table.add_column(str(key))

                for item in results[:20]:
                    row = [str(v) for v in item.values()]
                    table.add_row(*row)

                if len(results) > 20:
                    table.add_row(f"... and {len(results) - 20} more items")

                console.print(table)
            else:
                for i, item in enumerate(results[:20]):
                    console.print(f"{i+1}. {item}")
                if len(results) > 20:
                    console.print(f"... and {len(results) - 20} more items")
        else:
            console.print("[yellow]No results found[/yellow]")

        # Print any errors
        if not result.get("success", True):
            error = result.get("error", "Unknown error")
            console.print(f"[red]API Error:[/red] {error}")
