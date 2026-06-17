"""Get command for fetching data from sources."""

import asyncio
import json
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ayga_cli.client.redis import AygaParserRedisClient
from ayga_cli.config import get_config
from ayga_cli.exceptions import exit_codes
from ayga_cli.utils.fields import filter_fields
from ayga_cli.utils.sources_cache import load_cache

app = typer.Typer(help="Fetch data from a source", no_args_is_help=True)
console = Console()


def _build_epilog() -> str:
    cached = load_cache()
    if not cached:
        return "Use 'ayga_parser sources list' to see available sources."
    lines = ["Available sources (cached):"]
    for s in cached:
        lines.append(f"  {s['name']:<20} {s.get('description', '')}")
    return "\n".join(lines)


def _extract_list(result: dict) -> list:
    """Find the list of items inside a result dict."""
    if isinstance(result, list):
        return result
    for key in ("results", "result", "items", "data"):
        val = result.get(key)
        if isinstance(val, list):
            return val
        if isinstance(val, dict):
            for sub in ("results", "result", "items"):
                sub_val = val.get(sub)
                if isinstance(sub_val, list):
                    return sub_val
    return []


@app.command(name="get", epilog=_build_epilog())
def get_cmd(
    source: str = typer.Argument(..., help="Data source name (e.g., web-search)"),
    query: str = typer.Argument(..., help="Query string to fetch"),
    format_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    stream: bool = typer.Option(
        False, "--stream", "-s",
        help="Output as NDJSON — one record per line. Ideal for AI agents processing lists.",
    ),
    fields: Optional[str] = typer.Option(
        None, "--fields", "-f",
        help="Comma-separated fields to return (e.g. title,url,snippet). Supports dot-notation.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Show what would be sent to the server without executing.",
    ),
    timeout: int = typer.Option(300, "--timeout", help="Request timeout in seconds"),
    job_id: Optional[str] = typer.Option(None, "--job-id", help="Optional specific job ID"),
):
    """Fetch data from a source.

    Examples:
        ayga_parser get web-search "machine learning"
        ayga_parser get web-search "ML" --fields title,url,snippet
        ayga_parser get web-search "ML" --stream
        ayga_parser get web-search "ML" --dry-run
        ayga_parser get ai-answer "What is quantum computing?" --timeout 120
    """
    if not source or not source.strip():
        print("Error: Invalid input (empty source)", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_INPUT)
    if not query or not query.strip():
        print("Error: Invalid input (empty query)", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_INPUT)

    asyncio.run(_execute_get(source, query, format_json, stream, fields, dry_run, timeout, job_id))


async def _execute_get(
    source: str,
    query: str,
    format_json: bool,
    stream: bool,
    fields: Optional[str],
    dry_run: bool,
    timeout: int,
    job_id: Optional[str],
) -> None:
    config = get_config()
    redis_password = config.redis_password.get_secret_value() if config.redis_password else None
    password = config.password.get_secret_value() if config.password else None

    # --dry-run: show payload without executing
    if dry_run:
        import uuid
        preview_id = job_id or f"ayga_{source}_{uuid.uuid4().hex[:8]}"
        result_queue = f"ayga_results_{preview_id}"
        payload = [preview_id, source, query, {}, {"output_queue": result_queue}, {}]
        dry_info = {
            "dry_run": True,
            "queue": config.redis_queue,
            "payload": payload,
            "result_queue": result_queue,
            "timeout": timeout,
        }
        if format_json:
            print(json.dumps(dry_info, indent=2, ensure_ascii=False))
        else:
            console.print("[bold yellow]DRY RUN[/bold yellow] — would send to Redis Wrapper:")
            console.print(f"  Queue:        [cyan]{config.redis_queue}[/cyan]")
            console.print(f"  Payload:      [dim]{json.dumps(payload, ensure_ascii=False)}[/dim]")
            console.print(f"  Result queue: [cyan]{result_queue}[/cyan]")
            console.print(f"  Timeout:      {timeout}s")
            console.print("\n[dim]No data was fetched. Remove --dry-run to execute.[/dim]")
        return

    try:
        async with AygaParserRedisClient(
            redis_host=config.redis_host,
            redis_port=config.redis_port,
            redis_queue=config.redis_queue,
            redis_password=redis_password,
            password=password,
        ) as client:
            actual_job_id = await client.push(source=source, query=query, job_id=job_id)
            result_queue = f"ayga_results_{actual_job_id}"
            result = await client.pop(result_queue=result_queue, timeout=timeout)
    except (ConnectionError, OSError) as e:
        print(f"Error: Server unavailable — {e}", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_UNAVAILABLE)

    if result is None:
        print(f"Error: No response from server (timeout {timeout}s)", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_TIMEOUT)

    # --stream: NDJSON — extract list first, then apply --fields per item
    if stream:
        items = _extract_list(result) if isinstance(result, dict) else (result if isinstance(result, list) else [result])
        if not items:
            items = [result]
        for item in items:
            filtered = filter_fields(item, fields) if fields else item
            print(json.dumps(filtered, ensure_ascii=False))
        return

    # Apply --fields to full result (or to items list if present)
    if fields:
        items = _extract_list(result) if isinstance(result, dict) else None
        if items:
            result = {**result, **{k: v for k, v in result.items() if k not in ("results", "result", "items", "data")}}
            result = filter_fields({"results": [filter_fields(i, fields) for i in items]}, None)
        else:
            result = filter_fields(result, fields)

    # --json: structured JSON
    if format_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Human-readable
    _print_results(result)


def _print_results(result) -> None:
    """Print results in human-readable format."""
    if not result.get("success", True):
        error = result.get("error", "Unknown error")
        print(f"Error: {error}", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_GENERAL)

    items = _extract_list(result)
    if items:
        console.print(Panel.fit(
            f"[bold green]Success[/bold green] | Items: {len(items)}",
            border_style="green",
        ))
        table = Table(title="Results")
        if isinstance(items[0], dict):
            for key in items[0].keys():
                table.add_column(str(key))
            for item in items[:20]:
                table.add_row(*[str(v)[:120] for v in item.values()])
            if len(items) > 20:
                console.print(f"[dim]... and {len(items) - 20} more items[/dim]")
            console.print(table)
        else:
            for i, item in enumerate(items[:20]):
                console.print(f"{i+1}. {item}")
            if len(items) > 20:
                console.print(f"... and {len(items) - 20} more items")
    else:
        console.print(json.dumps(result, indent=2, ensure_ascii=False))
