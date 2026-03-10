"""Ping command to test HTTP connection to A-Parser."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from aparser_cli.client.http import AParserHttpClient
from aparser_cli.config import AParserConfig, get_config

app = typer.Typer(help="Test HTTP connection to A-Parser")
console = Console()


def _normalize_api_url(host: str, port: Optional[int]) -> str:
    """Normalize host and port options into an API URL."""
    base = host.rstrip("/")
    if base.endswith("/API"):
        return base
    if port is not None:
        return f"{base}:{port}/API"
    return f"{base}/API"


async def _ping_backend(config: AParserConfig, timeout: int) -> dict[str, Any]:
    """Perform a real ping request against the configured backend."""
    async with AParserHttpClient(config=config, timeout=timeout) as client:
        ok = await client.ping()
        auth = config.get_http_basic_auth()
        return {
            "status": "ok" if ok else "error",
            "reachable": ok,
            "message": "A-Parser API responded with pong" if ok else "A-Parser API did not return pong",
            "http_url": config.http_url,
            "basic_auth_enabled": bool(auth),
            "basic_auth_username": auth[0] if auth else None,
        }


@app.callback(invoke_without_command=True)
def ping(
    host: Optional[str] = typer.Option(None, "--host", help="Override A-Parser HTTP host or full API URL"),
    port: Optional[int] = typer.Option(None, "--port", help="Override A-Parser HTTP port when --host is a base host"),
    timeout: int = typer.Option(5, "--timeout", "-t", help="Connection timeout in seconds"),
    format_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Test HTTP connection and auth against the configured A-Parser server."""
    config = get_config().model_copy(deep=True)

    if host:
        config.http_url = _normalize_api_url(host, port)
    elif port is not None:
        if "://" in config.http_url:
            scheme, rest = config.http_url.split("://", 1)
            host_part = rest.split("/", 1)[0].split(":", 1)[0]
            config.http_url = f"{scheme}://{host_part}:{port}/API"

    try:
        result = asyncio.run(_ping_backend(config, timeout))

        if format_json:
            console.print(json.dumps(result, indent=2))
            return

        status_text = Text("OK", style="bold green")
        message = Text(result["message"])
        details = [
            f"URL: {result['http_url']}",
            f"HTTP Basic Auth: {'enabled' if result['basic_auth_enabled'] else 'disabled'}",
        ]
        if result["basic_auth_enabled"] and result["basic_auth_username"] is not None:
            details.append(f"HTTP Basic username: {result['basic_auth_username']!r}")

        panel = Panel(
            "\n".join([str(status_text), str(message), *details]),
            title="A-Parser Ping",
            border_style="green",
        )
        console.print(panel)

    except Exception as exc:
        payload = {
            "status": "error",
            "reachable": False,
            "message": str(exc),
            "http_url": config.http_url,
        }
        if format_json:
            console.print(json.dumps(payload, indent=2))
        else:
            panel = Panel(
                f"[bold red]FAILED[/bold red]\n{exc}\nURL: {config.http_url}",
                title="A-Parser Ping",
                border_style="red",
            )
            console.print(panel)
        raise typer.Exit(code=1) from exc
