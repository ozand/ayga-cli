"""+extract helper: fetch article URL and convert to Markdown."""

import asyncio
import sys

import typer

from ayga_cli.client.redis import AygaParserRedisClient
from ayga_cli.config import get_config
from ayga_cli.exceptions import exit_codes
from ayga_cli.utils.html_to_md import article_result_to_markdown

app = typer.Typer(help="Fetch a URL and return clean Markdown article text")


@app.command(name="extract")
def extract_cmd(
    url: str = typer.Argument(..., help="URL to extract article from"),
    timeout: int = typer.Option(300, "--timeout", help="Timeout in seconds"),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output raw JSON instead of Markdown"),
):
    """Fetch a URL and return clean Markdown.

    Internally uses the 'article' source. No parser or proxy configuration needed.

    Examples:
        ayga_parser +extract https://example.com/article
        ayga_parser +extract https://example.com/article --json
    """
    asyncio.run(_execute_extract(url, timeout, output_json))


async def _execute_extract(url: str, timeout: int, output_json: bool) -> None:
    import json

    config = get_config()
    redis_password = config.redis_password.get_secret_value() if config.redis_password else None
    password = config.password.get_secret_value() if config.password else None

    try:
        async with AygaParserRedisClient(
            redis_host=config.redis_host,
            redis_port=config.redis_port,
            redis_queue=config.redis_queue,
            redis_password=redis_password,
            password=password,
        ) as client:
            job_id = await client.push(source="article", query=url)
            result_queue = f"ayga_results_{job_id}"
            result = await client.pop(result_queue=result_queue, timeout=timeout)
    except (ConnectionError, OSError) as e:
        print(f"Error: Server unavailable — {e}", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_UNAVAILABLE)

    if result is None:
        print(f"Error: Timeout after {timeout}s", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_TIMEOUT)

    if output_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    md = article_result_to_markdown(result)
    print(md)
