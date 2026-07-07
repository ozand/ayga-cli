"""Get command for fetching data from sources."""

import asyncio
import json
import sys
import time
import uuid
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ayga_cli.client.http import AygaParserHttpClient
from ayga_cli.config import get_config
from ayga_cli.exceptions import AygaParserHTTPError, exit_codes
from ayga_cli.utils.fields import filter_fields
from ayga_cli.utils.sources_cache import load_cache, save_cache

app = typer.Typer(help="Fetch data from a source", no_args_is_help=True)
console = Console()

POLL_INTERVAL_SECONDS = 1.5


def _build_epilog() -> str:
    cached = load_cache()
    if not cached:
        return "Use 'ayga_parser sources list' to see available sources."
    lines = ["Available sources (cached):"]
    for s in cached:
        lines.append(f"  {s.get('id', s.get('name', '?')):<20} {s.get('description', '')}")
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
    source: str = typer.Argument(..., help="Data source name (e.g., perplexity)"),
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
    job_id: Optional[str] = typer.Option(None, "--job-id", help="Optional specific task ID"),
):
    """Fetch data from a source.

    Examples:
        ayga_parser get perplexity "machine learning"
        ayga_parser get perplexity "ML" --fields answer,sources
        ayga_parser get google_search "ML" --stream
        ayga_parser get google_search "ML" --dry-run
        ayga_parser get perplexity "What is quantum computing?" --timeout 120
    """
    if not source or not source.strip():
        print("Error: Invalid input (empty source)", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_INPUT)
    if not query or not query.strip():
        print("Error: Invalid input (empty query)", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_INPUT)

    asyncio.run(_execute_get(source, query, format_json, stream, fields, dry_run, timeout, job_id))


async def _resolve_aparser_name(config, source: str) -> Optional[str]:
    """Resolve a user-facing source id to its backend aparser_name.

    Uses the local sources cache first; on a cache miss (or if the source
    isn't found in the cache), fetches a fresh list from the server before
    giving up.
    """
    cached = load_cache()
    sources = cached or []

    match = next((s for s in sources if s.get("id") == source or s.get("name") == source), None)
    if match is not None:
        return match.get("aparser_name")

    # Cache miss — fetch fresh and try again
    async with AygaParserHttpClient(config=config) as client:
        response = await client.list_parsers()
    parsers = response.get("parsers", []) if isinstance(response, dict) else []
    if parsers:
        save_cache(parsers)

    match = next((s for s in parsers if s.get("id") == source or s.get("name") == source), None)
    if match is not None:
        return match.get("aparser_name")

    return None


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

    # --dry-run: show payload without executing
    if dry_run:
        preview_id = job_id or f"ayga_{source}_{uuid.uuid4().hex[:8]}"
        payload = {
            "task_id": preview_id,
            "parser": f"<aparser_name for '{source}'>",
            "preset": None,
            "query": query,
            "options": None,
            "results": None,
        }
        dry_info = {
            "dry_run": True,
            "url": f"{config.api_url}/parsers/tasks",
            "payload": payload,
            "result_queue": preview_id,
            "timeout": timeout,
        }
        if format_json:
            print(json.dumps(dry_info, indent=2, ensure_ascii=False))
        else:
            console.print("[bold yellow]DRY RUN[/bold yellow] — would POST to Redis Wrapper:")
            console.print(f"  URL:          [cyan]{dry_info['url']}[/cyan]")
            console.print(f"  Payload:      [dim]{json.dumps(payload, ensure_ascii=False)}[/dim]")
            console.print(f"  Timeout:      {timeout}s")
            console.print("\n[dim]No data was fetched. Remove --dry-run to execute.[/dim]")
        return

    try:
        aparser_name = await _resolve_aparser_name(config, source)
    except AygaParserHTTPError as e:
        print(f"Error: Server unavailable — {e}", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_UNAVAILABLE) from e

    if aparser_name is None:
        print(
            f"Error: Source '{source}' not found. Run 'ayga_parser sources list' to see "
            "available sources.",
            file=sys.stderr,
        )
        raise typer.Exit(code=exit_codes.ERROR_NOT_FOUND)

    try:
        async with AygaParserHttpClient(config=config) as client:
            submission = await client.submit_task(
                parser=aparser_name,
                query=query,
                task_id=job_id,
            )
            task_id = submission.get("task_id") or job_id
            if not task_id:
                print("Error: Server did not return a task_id", file=sys.stderr)
                raise typer.Exit(code=exit_codes.ERROR_GENERAL)

            result = await _poll_for_result(client, task_id, timeout)
    except (ConnectionError, OSError, AygaParserHTTPError) as e:
        print(f"Error: Server unavailable — {e}", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_UNAVAILABLE) from e

    if result is None:
        print(f"Error: No response from server (timeout {timeout}s)", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_TIMEOUT)

    # --stream: NDJSON — extract list first, then apply --fields per item
    if stream:
        if isinstance(result, dict):
            items = _extract_list(result)
        elif isinstance(result, list):
            items = result
        else:
            items = [result]
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
            excluded_keys = ("results", "result", "items", "data")
            result = {**result, **{k: v for k, v in result.items() if k not in excluded_keys}}
            result = filter_fields({"results": [filter_fields(i, fields) for i in items]}, None)
        else:
            result = filter_fields(result, fields)

    # --json: structured JSON
    if format_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Human-readable
    _print_results(result)


async def _poll_for_result(
    client: AygaParserHttpClient, task_id: str, timeout: int
) -> Optional[dict]:
    """Poll get_task_result until ready or timeout elapses.

    There is no server-side blocking-wait endpoint, so this polls on a
    fixed interval until the result is available or the timeout is hit.
    """
    deadline = time.monotonic() + timeout
    while True:
        result = await client.get_task_result(task_id)
        if result is not None:
            return result

        if time.monotonic() >= deadline:
            return None

        remaining = deadline - time.monotonic()
        await asyncio.sleep(min(POLL_INTERVAL_SECONDS, max(remaining, 0)))
        if time.monotonic() >= deadline:
            return None


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
            for key in items[0]:
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
