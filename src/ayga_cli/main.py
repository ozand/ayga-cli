"""Main entry point for ayga_parser CLI.

Implements the Typer application with command groups for:
- config: Configuration management
- parsers: Parser discovery and info
- redis: Redis queue operations
- http: HTTP API operations
- task: Task management
"""

from __future__ import annotations

import inspect
import sys
from typing import Optional

import click
import typer
import typer.core
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ayga_cli import __version__
from ayga_cli.config import AygaParserConfig, get_config, reload_config

# Import existing command modules
from ayga_cli.commands.ping import app as ping_app
from ayga_cli.commands.parsers import app as parsers_app
from ayga_cli.commands.presets import app as presets_app
from ayga_cli.commands.sources import app as sources_app
from ayga_cli.commands.redis import app as redis_app
from ayga_cli.commands.get import get_cmd as get_command
from ayga_cli.commands.test import test_cmd as test_command

# Initialize Rich console for pretty output
console = Console()


def _patch_click_make_metavar() -> None:
    """Patch Click/Typer metavar compatibility for Python 3.13 help output."""
    signature = inspect.signature(click.Parameter.make_metavar)
    if "ctx" not in signature.parameters:
        return

    original_make_metavar = click.Parameter.make_metavar

    def compat_make_metavar(self: click.Parameter, ctx: Optional[click.Context] = None) -> str:
        if ctx is None:
            ctx = click.Context(click.Command("ayga_parser"))
        return original_make_metavar(self, ctx)

    click.Parameter.make_metavar = compat_make_metavar

    def compat_typer_argument_make_metavar(
        self: typer.core.TyperArgument,
        ctx: Optional[click.Context] = None,
    ) -> str:
        if self.metavar is not None:
            return self.metavar

        var = (self.name or "").upper()
        if not self.required:
            var = f"[{var}]"

        type_signature = inspect.signature(self.type.get_metavar)
        if "ctx" in type_signature.parameters:
            type_var = self.type.get_metavar(self, ctx or click.Context(click.Command("ayga_parser")))
        else:
            type_var = self.type.get_metavar(self)

        if type_var:
            var += f":{type_var}"
        if self.nargs != 1:
            var += "..."
        return var

    typer.core.TyperArgument.make_metavar = compat_typer_argument_make_metavar


_patch_click_make_metavar()

# Create the main Typer app
app = typer.Typer(
    name="ayga_parser",
    help="ayga_parser CLI - Redis and HTTP API client for ayga_parser",
    no_args_is_help=True,
    add_completion=True,
    rich_markup_mode="rich",
)

# Create config command group
config_app = typer.Typer(
    name="config",
    help="Configuration management",
    no_args_is_help=True,
)

# Create http command group (placeholder for future implementation)
http_app = typer.Typer(
    name="http",
    help="HTTP API operations (fallback transport)",
    no_args_is_help=True,
)

# Create task command group (placeholder for future implementation)
task_app = typer.Typer(
    name="task",
    help="Task management",
    no_args_is_help=True,
)

# Register command groups with main app
app.add_typer(config_app)
app.add_typer(parsers_app, name="parsers")
app.add_typer(presets_app, name="presets")
app.add_typer(sources_app, name="sources")
app.add_typer(redis_app, name="redis")
app.add_typer(http_app)
app.add_typer(task_app)

# Add direct commands (not subcommands)
app.add_typer(ping_app, name="ping")
app.command(name="get")(get_command)
app.command(name="test")(test_command)


def version_callback(value: bool) -> None:
    """Display version information."""
    if value:
        console.print(f"[bold blue]ayga_parser CLI[/bold blue] version [green]{__version__}[/green]")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    config_file: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-V",
        help="Enable verbose output",
    ),
) -> None:
    """ayga_parser CLI - Redis and HTTP API client for ayga_parser.

    [bold]Quick Start:[/bold]
    [ayga_parser config init]     - Initialize configuration
    [ayga_parser ping]            - Test connection
    [ayga_parser parsers list]    - List available parsers

    [bold]Transports:[/bold]
    • Redis (primary): High-performance queue-based communication
    • HTTP (fallback): Direct synchronous requests

    For more help: [cyan]ayga_parser <command> --help[/cyan]
    """
    pass


# =============================================================================
# Config Commands
# =============================================================================

@config_app.command("init")
def config_init(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing configuration",
    ),
) -> None:
    """Initialize configuration interactively."""
    config_dir = AygaParserConfig.ensure_config_dir()
    config_file = config_dir / "config.yaml"

    if config_file.exists() and not force:
        console.print(f"[yellow]Config already exists at {config_file}[/yellow]")
        console.print("Use --force to overwrite")
        raise typer.Exit(1)

    console.print(Panel.fit(
        "[bold blue]ayga_parser CLI Configuration[/bold blue]\n\n"
        "This will create a configuration file at:\n"
        f"[cyan]{config_file}[/cyan]"
    ))

    # Collect configuration values
    http_url = typer.prompt(
        "HTTP API URL",
        default="http://127.0.0.1:9091/API",
    )
    redis_host = typer.prompt(
        "Redis host",
        default="127.0.0.1",
    )
    redis_port = typer.prompt(
        "Redis port",
        default="6379",
        type=int,
    )
    redis_queue = typer.prompt(
        "Redis queue name",
        default="ayga_parser_redis_api",
    )

    # Create config content
    config_content = f"""# ayga_parser CLI Configuration
# Generated by ayga_parser config init

# HTTP API Settings
http_url: "{http_url}"

# Redis Settings
redis_host: "{redis_host}"
redis_port: {redis_port}
redis_queue: "{redis_queue}"

# Default Settings
default_timeout: 300
default_preset: "default"
default_config_preset: "default"

# Logging
log_level: "INFO"
"""

    # Write config file
    config_file.write_text(config_content)
    console.print(f"[green]✓[/green] Configuration saved to {config_file}")

    # Ask about password
    if typer.confirm("Store ayga_parser password in OS keyring?", default=True):
        password = typer.prompt("ayga_parser password", hide_input=True)
        config = AygaParserConfig()
        try:
            config.set_password_keyring(password)
            console.print("[green]✓[/green] Password stored in OS keyring")
        except RuntimeError as e:
            console.print(f"[red]✗[/red] Failed to store password: {e}")


@config_app.command("show")
def config_show() -> None:
    """Display current configuration."""
    config = get_config()

    # Build display table
    from rich.table import Table

    table = Table(title="ayga_parser Configuration", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    # HTTP settings
    table.add_row("HTTP URL", config.http_url)

    # Redis settings
    table.add_row("Redis Host", config.redis_host)
    table.add_row("Redis Port", str(config.redis_port))
    table.add_row("Redis Queue", config.redis_queue)
    table.add_row("Redis Result Queue", config.redis_result_queue)
    table.add_row("Redis DB", str(config.redis_db))
    table.add_row("Redis SSL", str(config.redis_ssl))

    # Auth
    password_status = "[green]✓ Set[/green]" if config.get_password() else "[red]✗ Not set[/red]"
    table.add_row("API Password", password_status)

    # Defaults
    table.add_row("Default Timeout", f"{config.default_timeout}s")
    table.add_row("Default Preset", config.default_preset)
    table.add_row("Default Config Preset", config.default_config_preset)
    table.add_row("Log Level", config.log_level)

    console.print(table)

    # Show config file location
    config_file = AygaParserConfig.get_config_dir() / "config.yaml"
    console.print(f"\n[dim]Config file: {config_file}[/dim]")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key (e.g., redis.host)"),
    value: str = typer.Argument(..., help="Configuration value"),
) -> None:
    """Set a configuration value."""
    # Map dot notation to config keys
    key_mapping = {
        "http.url": "http_url",
        "redis.host": "redis_host",
        "redis.port": "redis_port",
        "redis.queue": "redis_queue",
        "redis.result_queue": "redis_result_queue",
        "redis.db": "redis_db",
        "redis.ssl": "redis_ssl",
        "timeout": "default_timeout",
        "preset": "default_preset",
        "config_preset": "default_config_preset",
        "log_level": "log_level",
    }

    normalized_key = key_mapping.get(key, key)

    # Read current config
    config_dir = AygaParserConfig.get_config_dir()
    config_file = config_dir / "config.yaml"

    if not config_file.exists():
        console.print(f"[red]✗[/red] Config file not found. Run 'ayga_parser config init' first.")
        raise typer.Exit(1)

    content = config_file.read_text()

    # Simple YAML line replacement (basic implementation)
    import re
    pattern = rf"^{normalized_key}:.*$"
    replacement = f"{normalized_key}: {value}"

    if re.search(pattern, content, re.MULTILINE):
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        config_file.write_text(new_content)
        console.print(f"[green]✓[/green] Updated {key} = {value}")
    else:
        # Append new key
        with open(config_file, "a") as f:
            f.write(f"\n{normalized_key}: {value}\n")
        console.print(f"[green]✓[/green] Added {key} = {value}")

    # Reload config
    reload_config()


@config_app.command("auth")
def config_auth(
    password: Optional[str] = typer.Option(
        None,
        "--password",
        "-p",
        help="ayga_parser password (will prompt if not provided)",
    ),
) -> None:
    """Store ayga_parser password in OS keyring."""
    if password is None:
        password = typer.prompt("ayga_parser password", hide_input=True)

    config = AygaParserConfig()
    try:
        config.set_password_keyring(password)
        console.print("[green]✓[/green] Password stored in OS keyring")
    except RuntimeError as e:
        console.print(f"[red]✗[/red] Failed to store password: {e}")
        raise typer.Exit(1)


# =============================================================================
# Placeholder Commands (to be implemented in Phase 2)
# =============================================================================

@http_app.command("request")
def http_request(
    parser: str = typer.Argument(..., help="Parser name"),
    query: str = typer.Argument(..., help="Query string"),
) -> None:
    """Send a synchronous HTTP request."""
    console.print("[yellow]Note:[/yellow] Implementation coming in Phase 2")


@task_app.command("list")
def task_list() -> None:
    """List active tasks."""
    console.print("[yellow]Note:[/yellow] Implementation coming in Phase 2")


if __name__ == "__main__":
    app()
