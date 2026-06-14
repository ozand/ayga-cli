"""Parser management commands."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from ayga_cli.manifest import (
    ManifestCache,
    FuzzySearchIndex,
    StaticManifest,
    get_manifest,
    search_parsers,
)
from ayga_cli.config import get_config

app = typer.Typer(help="Manage ayga-parser parsers")
console = Console()


def get_manifest_cache() -> ManifestCache:
    """Get a ManifestCache instance."""
    return ManifestCache()


def _load_manifest_with_fallback(use_cache: bool = True):
    """Load manifest from cache/API with static fallback."""
    if use_cache:
        cache = ManifestCache()
        manifest = cache.load()
        if manifest:
            return manifest
    return asyncio.run(get_manifest(verbose=False))


@app.command("list")
def list_parsers(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    format_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    use_cache: bool = typer.Option(True, "--cache/--no-cache", help="Use cached manifest"),
):
    """List all available parsers."""
    try:
        # Load manifest
        manifest = _load_manifest_with_fallback(use_cache=use_cache)

        if not manifest:
            console.print("[red]Error:[/red] No parser manifest available.")
            raise typer.Exit(code=1)

        # Filter by category if specified
        parsers = list(manifest.parsers.values())
        if category:
            parsers = [p for p in parsers if p.category == category]

        if format_json:
            import json
            data = [p.model_dump(mode="json") for p in parsers]
            console.print(json.dumps(data, indent=2))
        else:
            # Group by category
            categories = {}
            for parser in parsers:
                cat = parser.category or "Other"
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(parser)

            # Display in table
            table = Table(title=f"Available Parsers ({len(parsers)} total)")
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Category", style="magenta")
            table.add_column("Description", style="white")
            table.add_column("Presets", style="green")

            for cat in sorted(categories.keys()):
                for parser in sorted(categories[cat], key=lambda p: p.name):
                    presets_str = ", ".join(parser.presets[:3])
                    if len(parser.presets) > 3:
                        presets_str += "..."
                    table.add_row(
                        parser.name,
                        parser.category,
                        parser.description[:60] + "..." if len(parser.description) > 60 else parser.description,
                        presets_str,
                    )

            console.print(table)

            # Show cache info
            cache = ManifestCache()
            if cache.exists():
                age_hours = cache.get_age_hours()
                console.print(f"\n[dim]Cache age: {age_hours:.1f} hours[/dim]")

    except Exception as e:
        if format_json:
            import json
            console.print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("info")
def parser_info(
    name: str = typer.Argument(..., help="Parser name"),
    format_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Get detailed information about a specific parser."""
    try:
        if not name:
            raise typer.BadParameter("Parser name is required")

        # First try static manifest for required overrides info
        static = StaticManifest()
        static_parser = static.get_parser(name)

        # Also try to load from cache or fallback manifest for full details
        manifest = _load_manifest_with_fallback(use_cache=True)

        if not manifest and not static_parser:
            console.print(f"[red]Error:[/red] Parser '{name}' not found in static manifest or cache.")
            console.print("[yellow]Tip:[/yellow] Use 'ayga-parser parsers list-static' to see available parsers.")
            raise typer.Exit(code=1)

        parser = None
        if manifest:
            parser = manifest.get_parser(name)

        if not parser and not static_parser:
            # Try fuzzy search in static manifest
            matches = static.search(name, limit=3)
            if matches:
                console.print(f"[red]Error:[/red] Parser '{name}' not found.")
                console.print("\n[yellow]Did you mean:[/yellow]")
                for match in matches:
                    console.print(f"  - {match.get('name', '')}")
            else:
                console.print(f"[red]Error:[/red] Parser '{name}' not found.")
            raise typer.Exit(code=1)

        if format_json:
            import json
            output = {}
            if static_parser:
                output.update(static_parser)
            if parser:
                output.update(parser.model_dump(mode="json"))
            console.print(json.dumps(output, indent=2))
        else:
            # Use static info as base, enriched with cache info if available
            parser_name = name
            category = "Unknown"
            description = "No description available"
            presets = ["default"]
            keywords = []
            parameters = {}
            required_overrides = []
            default_overrides = {}

            if static_parser:
                parser_name = static_parser.get("name", name)
                category = static_parser.get("category", "Unknown")
                description = static_parser.get("description", description)
                presets = static_parser.get("presets", presets)
                keywords = static_parser.get("keywords", keywords)
                required_overrides = static_parser.get("required_overrides", [])
                default_overrides = static_parser.get("default_overrides", {})

            if parser:
                category = parser.category or category
                description = parser.description or description
                presets = parser.presets or presets
                keywords = parser.keywords or keywords
                parameters = parser.parameters or {}

            # Display detailed info
            title = Text(f"{parser_name}", style="bold cyan")

            details = [
                f"[bold]Category:[/bold] {category}",
                f"[bold]Description:[/bold] {description}",
                "",
                f"[bold]Presets:[/bold] {', '.join(presets)}",
            ]

            # Show required overrides (NEW)
            if required_overrides:
                details.extend(["", "[bold yellow]Required Overrides:[/bold yellow]"])
                for override in required_overrides:
                    default_val = default_overrides.get(override)
                    if default_val is not None:
                        details.append(f"  • {override} [dim](default: {default_val})[/dim]")
                    else:
                        details.append(f"  • {override} [red](must be specified)[/red]")

                # Show example usage
                details.extend(["", "[bold green]Example Usage:[/bold green]"])
                override_parts = []
                for override in required_overrides:
                    default_val = default_overrides.get(override)
                    if default_val is not None:
                        override_parts.append(f"{override}={default_val}")
                    else:
                        override_parts.append(f"{override}=YOUR_VALUE")

                example_cmd = f'ayga-parser run {parser_name} "your query" \\\n    --overrides "{",".join(override_parts)}"'
                details.append(f"[dim]{example_cmd}[/dim]")

                # Special note for proxyChecker
                if "proxyChecker" in required_overrides:
                    details.extend([
                        "",
                        "[bold red]⚠ Important:[/bold red] Without proxyChecker, you will get proxy errors.",
                        "   Make sure to specify a valid proxy checker preset."
                    ])

            if keywords:
                details.extend([
                    "",
                    f"[bold]Keywords:[/bold] {', '.join(keywords[:10])}",
                ])

            if parameters:
                details.extend(["", "[bold]Parameters:[/bold]"])
                for param_name, param in parameters.items():
                    req = "[red]required[/red]" if param.required else "[dim]optional[/dim]"
                    default = f" [dim](default: {param.default})[/dim]" if param.default is not None else ""
                    range_str = ""
                    if param.min is not None or param.max is not None:
                        range_str = f" [{param.min or ''}..{param.max or ''}]"
                    details.append(
                        f"  --{param_name} [{param.type}]{range_str}{default} - {param.description} ({req})"
                    )

            panel = Panel(
                "\n".join(details),
                title=title,
                border_style="cyan"
            )
            console.print(panel)

    except typer.Exit:
        raise
    except Exception as e:
        if format_json:
            import json
            console.print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("list-static")
def list_static_parsers(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    format_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List parsers from static manifest (no API call needed)."""
    try:
        static = StaticManifest()
        parsers = static.get_all_parsers()

        if not parsers:
            console.print("[red]Error:[/red] Static manifest not found or empty.")
            raise typer.Exit(code=1)

        # Filter by category if specified
        if category:
            parsers = {
                name: info for name, info in parsers.items()
                if info.get("category") == category
            }

        if format_json:
            import json
            data = list(parsers.values())
            console.print(json.dumps(data, indent=2))
        else:
            # Group by category
            categories = {}
            for name, parser in parsers.items():
                cat = parser.get("category") or "Other"
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(parser)

            # Display in table
            table = Table(title=f"Static Manifest Parsers ({len(parsers)} total)")
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Category", style="magenta")
            table.add_column("Description", style="white")
            table.add_column("Required Overrides", style="yellow")

            for cat in sorted(categories.keys()):
                for parser in sorted(categories[cat], key=lambda p: p.get("name", "")):
                    required = parser.get("required_overrides", [])
                    required_str = ", ".join(required) if required else "-"
                    desc = parser.get("description", "")
                    if len(desc) > 50:
                        desc = desc[:50] + "..."
                    table.add_row(
                        parser.get("name", ""),
                        parser.get("category", ""),
                        desc,
                        required_str,
                    )

            console.print(table)
            console.print(f"\n[dim]Version: {static.version}[/dim]")

    except Exception as e:
        if format_json:
            import json
            console.print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("search")
def search_command(
    query: str = typer.Argument(..., help="Search query"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum results"),
    min_score: float = typer.Option(0.3, "--min-score", "-s", help="Minimum confidence (0.0-1.0)"),
    format_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Search for parsers using fuzzy matching."""
    try:
        manifest = _load_manifest_with_fallback(use_cache=True)

        if not manifest:
            console.print("[red]Error:[/red] No parser manifest available.")
            raise typer.Exit(code=1)

        matches = search_parsers(
            query=query,
            manifest=manifest,
            limit=limit,
            min_score=min_score,
            category=category,
        )

        if not matches:
            console.print(f"[yellow]No parsers found matching '{query}'[/yellow]")
            return

        if format_json:
            import json
            data = [
                {
                    "name": m.parser.name,
                    "description": m.parser.description,
                    "category": m.parser.category,
                    "score": round(m.score, 2),
                    "match_type": m.match_type,
                }
                for m in matches
            ]
            console.print(json.dumps(data, indent=2))
        else:
            table = Table(title=f"Search Results for '{query}' ({len(matches)} found)")
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Category", style="magenta")
            table.add_column("Description", style="white")
            table.add_column("Score", style="green")
            table.add_column("Match", style="dim")

            for match in matches:
                desc = match.parser.description
                if len(desc) > 50:
                    desc = desc[:50] + "..."
                table.add_row(
                    match.parser.name,
                    match.parser.category,
                    desc,
                    f"{match.score:.2f}",
                    match.match_type,
                )

            console.print(table)

    except Exception as e:
        if format_json:
            import json
            console.print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("categories")
def list_categories(
    format_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all parser categories."""
    try:
        manifest = _load_manifest_with_fallback(use_cache=True)

        if not manifest:
            console.print("[red]Error:[/red] No parser manifest available.")
            raise typer.Exit(code=1)

        categories = {}
        for parser in manifest.parsers.values():
            cat = parser.category or "Other"
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1

        if format_json:
            import json
            data = [{"category": cat, "count": count} for cat, count in categories.items()]
            console.print(json.dumps(data, indent=2))
        else:
            table = Table(title="Parser Categories")
            table.add_column("Category", style="cyan")
            table.add_column("Count", style="green", justify="right")

            for cat in sorted(categories.keys()):
                table.add_row(cat, str(categories[cat]))

            console.print(table)
            console.print(f"\nTotal: {len(categories)} categories, {sum(categories.values())} parsers")

    except Exception as e:
        if format_json:
            import json
            console.print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("cache")
def cache_info(
    clear: bool = typer.Option(False, "--clear", help="Clear the cache"),
):
    """Show cache information or clear it."""
    cache = ManifestCache()

    if clear:
        cache.clear()
        console.print("[green]✓[/green] Cache cleared")
        return

    if not cache.exists():
        console.print("[yellow]Cache does not exist.[/yellow]")
        console.print("Use 'ayga-parser parsers list-static' for offline parser list.")
        return

    # Show cache info
    age_hours = cache.get_age_hours()
    is_expired = cache.is_expired()
    is_corrupted = cache.is_corrupted()

    table = Table(title="Cache Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Path", str(cache.cache_path))
    table.add_row("Age", f"{age_hours:.1f} hours")
    table.add_row("Status", "[red]EXPIRED[/red]" if is_expired else "[green]FRESH[/green]")
    table.add_row("Corrupted", "[red]YES[/red]" if is_corrupted else "[green]NO[/green]")

    # Load manifest for more details
    manifest = cache.load()
    if manifest:
        table.add_row("Version", manifest.version)
        table.add_row("Parser Count", str(manifest.parser_count))
        table.add_row("Created", manifest.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"))

    console.print(table)
