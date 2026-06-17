"""Get command for fetching data from sources."""

import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ayga_cli.client.redis import AygaParserRedisClient
from ayga_cli.config import get_config

app = typer.Typer(
    help="Fetch data from a source",
    no_args_is_help=True,
)
console = Console()


@app.command(name="get")
def get_cmd(
    source: str = typer.Argument(..., help="Data source name (e.g., web-search)"),
    query: str = typer.Argument(..., help="Query string to fetch"),
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
    job_id: Optional[str] = typer.Option(
        None,
        "--job-id",
        help="Optional specific job ID to use",
    ),
):
    """Fetch data from a source.

    Examples:
        ayga_parser get web-search "machine learning"
        ayga_parser get ai-answer "What is quantum computing?"
    """
    asyncio.run(_execute_get(source, query, format_json, timeout, job_id))


async def _execute_get(
    source: str, query: str, format_json: bool, timeout: int, job_id: Optional[str]
) -> None:
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
        # Push job - push returns job_id as string
        actual_job_id = await client.push(
            source=source,
            query=query,
            job_id=job_id,
        )

        result_queue = f"ayga_results_{actual_job_id}"

        # Pop result
        result = await client.pop(
            result_queue=result_queue,
            timeout=timeout,
        )

    if not result:
        if format_json:
            console.print(json.dumps({
                "status": "error",
                "error": f"No response from server (timeout {timeout}s)",
            }, indent=2))
        else:
            console.print(f"[red]Error:[/red] No response from server (timeout {timeout}s)")
        raise typer.Exit(code=1)

    # Output results
    if format_json:
        console.print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        _print_results(result)


def _print_results(result: dict) -> None:
    """Print results in human-readable format."""
    
    # For now, check if success is false
    if not result.get("success", True):
        error = result.get("error", "Unknown error")
        console.print(f"[red]Error:[/red] {error}")
        return
        
    data = result.get("data", {})
    results = data.get("results", [])

    if not results and "result" in data:
        # Fallback if structure is different
        results = data.get("result", [])
        if not isinstance(results, list):
            results = [results]

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
                table.add_row(*(["..."] * len(results[0])))
                console.print(f"[dim]... and {len(results) - 20} more items[/dim]")

            console.print(table)
        else:
            for i, item in enumerate(results[:20]):
                console.print(f"{i+1}. {item}")
            if len(results) > 20:
                console.print(f"... and {len(results) - 20} more items")
    else:
        console.print("[yellow]No results found[/yellow]")
