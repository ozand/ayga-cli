"""Redis queue management commands for ayga_parser CLI."""

import asyncio
import json
import uuid
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from ayga_cli.client.redis import AygaParserRedisClient
from ayga_cli.config import get_config
from ayga_cli.presets import get_preset_manager

app = typer.Typer(help="Manage Redis task queues")
console = Console()


def parse_options(options_str: Optional[str]) -> list[dict]:
    """Parse options string into list of option dicts.

    Args:
        options_str: Comma-separated key=value pairs or JSON array

    Returns:
        List of option dictionaries
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
                    if value.lower() == "true":
                        value = True
                    elif value.lower() == "false":
                        value = False

            options.append({"id": key, "value": value})

    return options


@app.command("status")
def redis_status(
    queue: Optional[str] = typer.Option(None, "--queue", "-q", help="Redis queue name (default: from config)"),
    format_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Check Redis queue status and connection health.

    Shows queue depth, connection status, and other queue statistics.

    Examples:
        ayga_parser redis status
        ayga_parser redis status --queue custom_queue
        ayga_parser redis status --json
    """
    try:
        config = get_config()
        queue_name = queue or config.redis_queue

        async def check_status():
            async with AygaParserRedisClient(
                redis_host=config.redis_host,
                redis_port=config.redis_port,
                redis_queue=queue_name,
                redis_password=config.redis_password.get_secret_value() if config.redis_password else None,
                password=config.get_password(),
            ) as client:
                # Check connection health
                is_healthy = await client.health_check()

                # Get queue depth
                try:
                    queue_depth = await client.queue_depth(queue_name)
                except Exception:
                    queue_depth = None

                return {
                    "healthy": is_healthy,
                    "queue_name": queue_name,
                    "queue_depth": queue_depth,
                    "redis_host": config.redis_host,
                    "redis_port": config.redis_port,
                }

        status = asyncio.run(check_status())

        if format_json:
            console.print(json.dumps(status, indent=2))
        else:
            if not status["healthy"]:
                console.print("[red]✗[/red] Redis connection failed")
                console.print(f"[dim]Host: {status['redis_host']}:{status['redis_port']}[/dim]")
                raise typer.Exit(code=1)

            # Display status table
            table = Table(title="Redis Queue Status")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Connection", "[green]✓ Healthy[/green]")
            table.add_row("Host", f"{status['redis_host']}:{status['redis_port']}")
            table.add_row("Queue", status["queue_name"])

            if status["queue_depth"] is not None:
                depth = status["queue_depth"]
                depth_str = str(depth)
                if depth > 100:
                    depth_str = f"[yellow]{depth}[/yellow] (high)"
                elif depth > 0:
                    depth_str = f"[green]{depth}[/green]"
                else:
                    depth_str = f"[dim]{depth}[/dim]"
                table.add_row("Queue Depth", depth_str)
            else:
                table.add_row("Queue Depth", "[dim]N/A[/dim]")

            console.print(table)

            # Show interpretation
            if status["queue_depth"] == 0:
                console.print("\n[dim]Queue is empty. Ready for new tasks.[/dim]")
            elif status["queue_depth"] and status["queue_depth"] > 100:
                console.print("\n[yellow]Warning:[/yellow] Queue has many pending tasks.")

    except Exception as e:
        if format_json:
            console.print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("push")
def redis_push(
    parser: str = typer.Argument(..., help="Parser name (e.g., FreeAI::Perplexity)"),
    query: str = typer.Argument(..., help="Query to process"),
    preset: str = typer.Option("default", "--preset", "-p", help="Parser preset name"),
    options: Optional[str] = typer.Option(
        None,
        "--options",
        "-o",
        help="Options as key=value pairs (e.g., 'proxyChecker=reproxy_v4,timeout=120')",
    ),
    result_queue: Optional[str] = typer.Option(
        None,
        "--result-queue",
        "-r",
        help="Custom result queue name (default: auto-generated)",
    ),
    config_preset: str = typer.Option(
        "default",
        "--config-preset",
        help="Config preset for thread pool settings",
    ),
    wait: bool = typer.Option(
        False,
        "--wait",
        "-w",
        help="Wait for result after pushing",
    ),
    timeout: int = typer.Option(
        300,
        "--timeout",
        "-t",
        help="Timeout in seconds for --wait",
    ),
    format_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Push a task to Redis queue.

    Pushes a parsing task to the ayga_parser Redis queue for async processing.
    Returns immediately with a job ID unless --wait is specified.

    Examples:
        # Push a simple task
        ayga_parser redis push "FreeAI::Perplexity" "What is machine learning?"

        # Push with preset and options
        ayga_parser redis push "FreeAI::Perplexity" "query" \
            --preset default \
            --options "proxyChecker=reproxy_v4,timeout=120"

        # Push and wait for result
        ayga_parser redis push "SE::Google" "python tutorial" --wait --timeout 60
    """
    try:
        config = get_config()
        parsed_options = parse_options(options)

        # Generate job ID
        job_id = str(uuid.uuid4())

        async def do_push():
            async with AygaParserRedisClient(
                redis_host=config.redis_host,
                redis_port=config.redis_port,
                redis_queue=config.redis_queue,
                redis_password=config.redis_password.get_secret_value() if config.redis_password else None,
                password=config.get_password(),
            ) as client:
                # Push to queue
                actual_result_queue = await client.push(
                    parser=parser,
                    query=query,
                    preset=preset,
                    config_preset=config_preset,
                    result_queue=result_queue,
                    options=parsed_options,
                )

                result = {
                    "job_id": job_id,
                    "parser": parser,
                    "query": query,
                    "preset": preset,
                    "result_queue": actual_result_queue,
                    "status": "queued",
                }

                # Wait for result if requested
                if wait:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                    ) as progress:
                        task = progress.add_task("Waiting for result...", total=None)

                        pop_result = await client.pop(
                            result_queue=actual_result_queue,
                            timeout=timeout,
                        )

                        progress.stop()

                        if pop_result is None:
                            result["status"] = "timeout"
                            result["message"] = f"No result after {timeout}s"
                        else:
                            result["status"] = "completed"
                            result["result"] = pop_result

                return result

        result = asyncio.run(do_push())

        if format_json:
            console.print(json.dumps(result, indent=2))
        else:
            if result["status"] == "timeout":
                console.print(f"[yellow]Timeout:[/yellow] {result['message']}")
                console.print(f"[dim]Result queue: {result['result_queue']}[/dim]")
                console.print("Use [cyan]ayga_parser redis pop {result_queue}[/cyan] to check later.")
                raise typer.Exit(code=124)

            status_style = "bold green" if result["status"] == "completed" else "bold yellow"
            status_text = "✓ Completed" if result["status"] == "completed" else "→ Queued"

            details = [
                f"[bold]Job ID:[/bold] {result['job_id']}",
                f"[bold]Parser:[/bold] {result['parser']}",
                f"[bold]Query:[/bold] {result['query']}",
                f"[bold]Result Queue:[/bold] {result['result_queue']}",
            ]

            if result["status"] == "completed" and "result" in result:
                # Show result summary
                result_data = result["result"]
                if isinstance(result_data, dict):
                    if "results" in result_data:
                        results = result_data["results"]
                        details.append(f"[bold]Results:[/bold] {len(results)} items")
                    elif "data" in result_data and isinstance(result_data["data"], dict):
                        data = result_data["data"]
                        if "results" in data:
                            details.append(f"[bold]Results:[/bold] {len(data['results'])} items")

            panel = Panel(
                f"[{status_style}]{status_text}[/{status_style}]\n" + "\n".join(details),
                title="Redis Push",
                border_style="green" if result["status"] == "completed" else "yellow"
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


@app.command("pop")
def redis_pop(
    result_queue: str = typer.Argument(..., help="Result queue name to pop from"),
    timeout: int = typer.Option(
        0,
        "--timeout",
        "-t",
        help="Timeout in seconds (0 = non-blocking)",
    ),
    format_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Pop a result from a Redis result queue.

    Retrieves results from a specific result queue. Use with --timeout to wait
    for results, or without for immediate check.

    Examples:
        # Non-blocking check
        ayga_parser redis pop my_results

        # Wait up to 60 seconds for result
        ayga_parser redis pop my_results --timeout 60
    """
    try:
        config = get_config()

        async def do_pop():
            async with AygaParserRedisClient(
                redis_host=config.redis_host,
                redis_port=config.redis_port,
                redis_queue=config.redis_queue,
                redis_password=config.redis_password.get_secret_value() if config.redis_password else None,
                password=config.get_password(),
            ) as client:
                result = await client.pop(
                    result_queue=result_queue,
                    timeout=timeout,
                )
                return result

        result = asyncio.run(do_pop())

        if result is None:
            if format_json:
                console.print(json.dumps({
                    "status": "no_result",
                    "message": "No result available" if timeout == 0 else f"Timeout after {timeout}s"
                }, indent=2))
            else:
                if timeout == 0:
                    console.print("[yellow]No result available[/yellow]")
                else:
                    console.print(f"[yellow]Timeout:[/yellow] No result after {timeout}s")
            raise typer.Exit(code=124)

        if format_json:
            console.print(json.dumps(result, indent=2))
        else:
            console.print("[green]✓[/green] Result received")
            console.print(json.dumps(result, indent=2, ensure_ascii=False))

    except typer.Exit:
        raise
    except Exception as e:
        if format_json:
            console.print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("depth")
def redis_depth(
    queue: Optional[str] = typer.Option(None, "--queue", "-q", help="Queue name (default: from config)"),
    format_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show queue depth (number of pending tasks).

    Examples:
        ayga_parser redis depth
        ayga_parser redis depth --queue custom_queue
    """
    try:
        config = get_config()
        queue_name = queue or config.redis_queue

        async def get_depth():
            async with AygaParserRedisClient(
                redis_host=config.redis_host,
                redis_port=config.redis_port,
                redis_queue=config.redis_queue,
                redis_password=config.redis_password.get_secret_value() if config.redis_password else None,
                password=config.get_password(),
            ) as client:
                return await client.queue_depth(queue_name)

        depth = asyncio.run(get_depth())

        if format_json:
            console.print(json.dumps({
                "queue": queue_name,
                "depth": depth,
            }, indent=2))
        else:
            if depth == 0:
                console.print(f"[dim]Queue '{queue_name}' is empty[/dim]")
            elif depth < 10:
                console.print(f"[green]Queue '{queue_name}' has {depth} pending task(s)[/green]")
            elif depth < 100:
                console.print(f"[yellow]Queue '{queue_name}' has {depth} pending tasks[/yellow]")
            else:
                console.print(f"[red]Queue '{queue_name}' has {depth} pending tasks (backlog)[/red]")

    except Exception as e:
        if format_json:
            console.print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
