"""+research helper: combine web-search + ai-answer for a query."""

import asyncio
import json
import sys

import typer

from ayga_cli.client.redis import AygaParserRedisClient
from ayga_cli.config import get_config
from ayga_cli.exceptions import exit_codes

app = typer.Typer(help="Research a topic using multiple sources (web-search + ai-answer)")


@app.command(name="research")
def research_cmd(
    query: str = typer.Argument(..., help="Research query"),
    timeout: int = typer.Option(300, "--timeout", help="Timeout per source in seconds"),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Research a topic by combining web-search and ai-answer results.

    Sends two parallel jobs to the server and combines results.

    Examples:
        ayga_parser +research "quantum computing"
        ayga_parser +research "climate change 2025" --json
    """
    asyncio.run(_execute_research(query, timeout, output_json))


async def _execute_research(query: str, timeout: int, output_json: bool) -> None:
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
            # Push both jobs in parallel
            web_job, ai_job = await asyncio.gather(
                client.push(source="web-search", query=query),
                client.push(source="ai-answer", query=query),
            )
            # Collect results sequentially (with shared timeout)
            web_result, ai_result = await asyncio.gather(
                client.pop(f"ayga_results_{web_job}", timeout=timeout),
                client.pop(f"ayga_results_{ai_job}", timeout=timeout),
            )
    except (ConnectionError, OSError) as e:
        print(f"Error: Server unavailable — {e}", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_UNAVAILABLE)

    combined = {
        "query": query,
        "web_search": web_result,
        "ai_answer": ai_result,
    }

    if output_json:
        print(json.dumps(combined, indent=2, ensure_ascii=False))
        return

    # Human-readable
    if ai_result:
        print("## AI Answer\n")
        answer = ai_result.get("answer") or ai_result.get("text") or json.dumps(ai_result, ensure_ascii=False)
        print(answer)
        print()

    if web_result:
        results = web_result.get("results", web_result.get("result", []))
        if not isinstance(results, list):
            results = [results]
        print(f"## Web Search ({len(results)} results)\n")
        for r in results[:5]:
            if isinstance(r, dict):
                title = r.get("title", "")
                url = r.get("url", r.get("link", ""))
                snippet = r.get("snippet", r.get("description", ""))
                print(f"- [{title}]({url})")
                if snippet:
                    print(f"  {snippet}")
            else:
                print(f"- {r}")

    if not ai_result and not web_result:
        print("Error: No results from either source (timeout)", file=sys.stderr)
        raise typer.Exit(code=exit_codes.ERROR_TIMEOUT)
