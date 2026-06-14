"""Preset management commands for ayga-parser CLI."""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ayga_cli.presets import get_preset_manager, PresetManager

app = typer.Typer(help="Manage parser presets")
console = Console()


def get_manager() -> PresetManager:
    """Get preset manager instance."""
    return get_preset_manager()


@app.command("list")
def list_presets(
    format_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all saved presets."""
    try:
        manager = get_manager()
        presets = manager.list_presets()

        if not presets:
            if format_json:
                console.print(json.dumps([], indent=2))
            else:
                console.print("[yellow]No presets saved yet.[/yellow]")
                console.print("Use [cyan]ayga-parser presets save <name> <parser>[/cyan] to create one.")
            return

        if format_json:
            data = [
                {
                    "name": p.name,
                    "parser": p.parser,
                    "description": p.description,
                    "overrides": p.overrides,
                }
                for p in presets
            ]
            console.print(json.dumps(data, indent=2))
        else:
            table = Table(title="Saved Presets")
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Parser", style="magenta")
            table.add_column("Description", style="white")
            table.add_column("Overrides", style="green")

            for preset in presets:
                overrides_str = ", ".join(
                    f"{k}={v}" for k, v in preset.overrides.items()
                )
                if len(overrides_str) > 40:
                    overrides_str = overrides_str[:37] + "..."

                table.add_row(
                    preset.name,
                    preset.parser,
                    preset.description[:50] if preset.description else "—",
                    overrides_str if overrides_str else "—",
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(presets)} preset(s)[/dim]")

    except Exception as e:
        if format_json:
            console.print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("save")
def save_preset(
    name: str = typer.Argument(..., help="Preset name (unique identifier)"),
    parser: str = typer.Argument(..., help="Parser name (e.g., FreeAI::Perplexity)"),
    description: str = typer.Option("", "--description", "-d", help="Preset description"),
    overrides: str = typer.Option(
        "",
        "--overrides",
        "-o",
        help="Overrides as key=value pairs (e.g., 'proxyChecker=reproxy_v4,timeout=120')",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing preset",
    ),
    format_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Save a new preset with parser and overrides.

    Examples:
        # Save a simple preset
        ayga-parser presets save perplexity-business "FreeAI::Perplexity" \
            --description "For business queries" \
            --overrides "proxyChecker=reproxy_v4,timeout=120"

        # Save with JSON overrides
        ayga-parser presets save google-search "SE::Google" \
            --overrides '{"pagecount": 5, "region": "us"}'
    """
    try:
        manager = get_manager()

        # Check if preset already exists
        if manager.exists(name) and not force:
            if format_json:
                console.print(json.dumps({
                    "status": "error",
                    "message": f"Preset '{name}' already exists. Use --force to overwrite."
                }, indent=2))
            else:
                console.print(f"[red]Error:[/red] Preset '{name}' already exists.")
                console.print("Use [cyan]--force[/cyan] to overwrite.")
            raise typer.Exit(code=1)

        # Parse overrides
        overrides_dict = manager.parse_overrides_string(overrides)

        # Save preset
        preset = manager.save_preset(
            name=name,
            parser=parser,
            description=description,
            overrides=overrides_dict,
        )

        if format_json:
            console.print(json.dumps({
                "status": "success",
                "preset": {
                    "name": preset.name,
                    "parser": preset.parser,
                    "description": preset.description,
                    "overrides": preset.overrides,
                }
            }, indent=2))
        else:
            status = Text("✓ Preset Saved", style="bold green")
            details = [
                f"[bold]Name:[/bold] {preset.name}",
                f"[bold]Parser:[/bold] {preset.parser}",
            ]
            if preset.description:
                details.append(f"[bold]Description:[/bold] {preset.description}")
            if preset.overrides:
                overrides_str = ", ".join(
                    f"{k}={v}" for k, v in preset.overrides.items()
                )
                details.append(f"[bold]Overrides:[/bold] {overrides_str}")

            panel = Panel(
                f"{status}\n" + "\n".join(details),
                title="Preset Saved",
                border_style="green"
            )
            console.print(panel)

    except typer.Exit:
        raise
    except Exception as e:
        if format_json:
            console.print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("show")
def show_preset(
    name: str = typer.Argument(..., help="Preset name to show"),
    format_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show detailed information about a preset."""
    try:
        manager = get_manager()
        preset = manager.get_preset(name)

        if not preset:
            if format_json:
                console.print(json.dumps({
                    "status": "error",
                    "message": f"Preset '{name}' not found"
                }, indent=2))
            else:
                console.print(f"[red]Error:[/red] Preset '{name}' not found.")
                console.print("Use [cyan]ayga-parser presets list[/cyan] to see available presets.")
            raise typer.Exit(code=1)

        if format_json:
            console.print(json.dumps({
                "name": preset.name,
                "parser": preset.parser,
                "description": preset.description,
                "overrides": preset.overrides,
            }, indent=2))
        else:
            title = Text(f"Preset: {preset.name}", style="bold cyan")

            details = [
                f"[bold]Parser:[/bold] {preset.parser}",
            ]

            if preset.description:
                details.append(f"[bold]Description:[/bold] {preset.description}")
            else:
                details.append("[dim]No description[/dim]")

            if preset.overrides:
                details.extend(["", "[bold]Overrides:[/bold]"])
                for key, value in preset.overrides.items():
                    details.append(f"  [cyan]{key}:[/cyan] {value}")
            else:
                details.extend(["", "[dim]No overrides configured[/dim]"])

            # Show usage example
            details.extend([
                "",
                "[bold]Usage:[/bold]",
                f"  [cyan]ayga-parser run --preset {preset.name} \"your query\"[/cyan]",
            ])

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
            console.print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("delete")
def delete_preset(
    name: str = typer.Argument(..., help="Preset name to delete"),
    confirm: bool = typer.Option(
        True,
        "--confirm/--no-confirm",
        help="Confirm before deletion",
    ),
    format_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Delete a preset."""
    try:
        manager = get_manager()

        if not manager.exists(name):
            if format_json:
                console.print(json.dumps({
                    "status": "error",
                    "message": f"Preset '{name}' not found"
                }, indent=2))
            else:
                console.print(f"[red]Error:[/red] Preset '{name}' not found.")
            raise typer.Exit(code=1)

        # Confirm deletion
        if confirm and not format_json:
            if not typer.confirm(f"Delete preset '{name}'?"):
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit()

        # Delete preset
        if manager.delete_preset(name):
            if format_json:
                console.print(json.dumps({
                    "status": "success",
                    "message": f"Preset '{name}' deleted"
                }, indent=2))
            else:
                console.print(f"[green]✓[/green] Preset '{name}' deleted")
        else:
            if format_json:
                console.print(json.dumps({
                    "status": "error",
                    "message": f"Failed to delete preset '{name}'"
                }, indent=2))
            else:
                console.print(f"[red]✗[/red] Failed to delete preset '{name}'")
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        if format_json:
            console.print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
