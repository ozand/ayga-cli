"""Sources command for listing available data sources."""

import asyncio
import json

import typer
from rich.console import Console
from rich.table import Table

from ayga_cli.client.redis import AygaParserRedisClient
from ayga_cli.config import get_config

app = typer.Typer(
    help="Manage data sources",
    no_args_is_help=True,
)
console = Console()


@app.command(name="list")
def list_cmd(
    format_json: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output as JSON",
    ),
):
    """List available sources from the server."""
    asyncio.run(_execute_list(format_json))


async def _execute_list(format_json: bool) -> None:
    config = get_config()

    redis_password = config.redis_password.get_secret_value() if config.redis_password else None
    password = config.password.get_secret_value() if config.password else None

    async with AygaParserRedisClient(
        redis_host=config.redis_host,
        redis_port=config.redis_port,
        redis_queue=config.redis_queue,
        redis_password=redis_password,
        password=password,
    ) as client:
        sources = await client.get_sources()

    if not sources:
        if format_json:
            console.print(json.dumps({
                "status": "error",
                "message": "No sources configured on server. Contact your administrator.",
            }, indent=2))
        else:
            console.print("[yellow]No sources configured on server. Contact your administrator.[/yellow]")
        return

    if format_json:
        console.print(json.dumps({"sources": sources}, indent=2, ensure_ascii=False))
        return

    table = Table(title="Available Sources")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Category", style="magenta")
    table.add_column("Description", style="green")

    for source in sources:
        table.add_row(
            source.get("name", "Unknown"),
            source.get("category", "Uncategorized"),
            source.get("description", ""),
        )

    console.print(table)
