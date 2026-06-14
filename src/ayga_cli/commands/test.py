"""Test command for checking parser configuration and connectivity."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ayga_cli.client.http import AygaParserHttpClient
from ayga_cli.config import get_config
from ayga_cli.static_manifest import (
    get_parser_defaults,
    get_default_overrides,
    get_required_overrides,
    validate_overrides,
)

app = typer.Typer(help="Test parser configuration and connectivity")
console = Console()


@app.command(name="test")
def test_cmd(
    parser: str = typer.Argument(..., help="Parser to test"),
    query: str = typer.Option("test", "--query", "-q", help="Test query"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    timeout: int = typer.Option(
        120,
        "--timeout",
        "-t",
        help="Request timeout in seconds",
    ),
    format_json: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output as JSON",
    ),
):
    """Test parser with a simple query.

    This command performs a complete test of the parser configuration:
    1. Checks if parser exists in static manifest
    2. Applies default overrides
    3. Validates required overrides
    4. Executes a test request
    5. Shows result or error with recommendations

    Examples:
        # Basic test
        ayga_parser test FreeAI::Perplexity

        # Test with custom query
        ayga_parser test SE::Google --query "machine learning"

        # Verbose output
        ayga_parser test FreeAI::Perplexity --verbose

        # JSON output
        ayga_parser test FreeAI::Perplexity --json
    """
    config = get_config()

    # Initialize test results
    test_results = {
        "parser": parser,
        "query": query,
        "steps": [],
        "success": False,
        "duration_ms": 0,
    }

    start_time = time.time()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=format_json,
        ) as progress:

            # Step 1: Check static manifest
            task = progress.add_task("Checking static manifest...", total=None)
            defaults = get_parser_defaults(parser)

            if defaults:
                test_results["steps"].append({
                    "name": "manifest_check",
                    "status": "pass",
                    "message": f"Parser found in static manifest ({defaults.category})",
                })
                if not format_json:
                    progress.update(task, description=f"[green]✓[/green] Parser found in static manifest")
            else:
                test_results["steps"].append({
                    "name": "manifest_check",
                    "status": "warning",
                    "message": "Parser not in static manifest (will try anyway)",
                })
                if not format_json:
                    progress.update(task, description=f"[yellow]![/yellow] Parser not in static manifest")

            # Step 2: Apply default overrides
            task = progress.add_task("Applying default overrides...", total=None)
            default_overrides = get_default_overrides(parser)

            if default_overrides:
                test_results["steps"].append({
                    "name": "default_overrides",
                    "status": "pass",
                    "message": f"Default overrides applied: {default_overrides}",
                })
                if not format_json:
                    overrides_str = ", ".join(f"{k}={v}" for k, v in default_overrides.items())
                    progress.update(task, description=f"[green]✓[/green] Default overrides: {overrides_str}")
            else:
                test_results["steps"].append({
                    "name": "default_overrides",
                    "status": "info",
                    "message": "No default overrides for this parser",
                })
                if not format_json:
                    progress.update(task, description="[dim]○ No default overrides[/dim]")

            # Step 3: Validate required overrides
            task = progress.add_task("Validating overrides...", total=None)
            all_overrides = default_overrides.copy()

            is_valid, missing = validate_overrides(parser, all_overrides)

            if is_valid:
                test_results["steps"].append({
                    "name": "validation",
                    "status": "pass",
                    "message": "All required overrides present",
                })
                if not format_json:
                    progress.update(task, description="[green]✓[/green] All required overrides present")
            else:
                test_results["steps"].append({
                    "name": "validation",
                    "status": "fail",
                    "message": f"Missing required overrides: {missing}",
                })
                if not format_json:
                    progress.update(task, description=f"[red]✗[/red] Missing: {', '.join(missing)}")

                # Cannot proceed without required overrides
                test_results["success"] = False
                test_results["error"] = f"Missing required overrides: {missing}"
                test_results["duration_ms"] = int((time.time() - start_time) * 1000)

                if format_json:
                    console.print(json.dumps(test_results, indent=2, ensure_ascii=False))
                else:
                    _print_test_failure(test_results, defaults)

                raise typer.Exit(code=1)

            # Step 4: Execute test request
            task = progress.add_task("Sending test request...", total=None)

            try:
                result = asyncio.run(_execute_test(
                    parser=parser,
                    query=query,
                    overrides=all_overrides,
                    timeout=timeout,
                ))

                test_results["steps"].append({
                    "name": "request",
                    "status": "pass",
                    "message": "Request sent successfully",
                })
                if not format_json:
                    progress.update(task, description="[green]✓[/green] Request sent")

            except Exception as e:
                test_results["steps"].append({
                    "name": "request",
                    "status": "fail",
                    "message": f"Request failed: {str(e)}",
                })
                if not format_json:
                    progress.update(task, description=f"[red]✗[/red] Request failed: {e}")

                test_results["success"] = False
                test_results["error"] = str(e)
                test_results["duration_ms"] = int((time.time() - start_time) * 1000)

                if format_json:
                    console.print(json.dumps(test_results, indent=2, ensure_ascii=False))
                else:
                    _print_test_failure(test_results, defaults)

                raise typer.Exit(code=1)

            # Step 5: Process response
            task = progress.add_task("Processing response...", total=None)

            if result.get("success", False):
                data = result.get("data", {})
                results = data.get("results", [])

                test_results["steps"].append({
                    "name": "response",
                    "status": "pass",
                    "message": f"Response received with {len(results)} results",
                })
                test_results["success"] = True
                test_results["result_count"] = len(results)
                test_results["results"] = results[:5] if verbose else []  # Limit in verbose mode

                if not format_json:
                    progress.update(task, description=f"[green]✓[/green] Response received ({len(results)} results)")
            else:
                error = result.get("error", "Unknown API error")
                test_results["steps"].append({
                    "name": "response",
                    "status": "warning",
                    "message": f"API returned error: {error}",
                })
                test_results["success"] = True  # Test itself succeeded, API returned error
                test_results["api_error"] = error

                if not format_json:
                    progress.update(task, description=f"[yellow]![/yellow] API error: {error}")

        # Calculate duration
        test_results["duration_ms"] = int((time.time() - start_time) * 1000)

        # Output results
        if format_json:
            console.print(json.dumps(test_results, indent=2, ensure_ascii=False))
        else:
            _print_test_success(test_results, defaults, verbose)

    except typer.Exit:
        raise
    except Exception as e:
        test_results["success"] = False
        test_results["error"] = str(e)
        test_results["duration_ms"] = int((time.time() - start_time) * 1000)

        if format_json:
            console.print(json.dumps(test_results, indent=2, ensure_ascii=False))
        else:
            console.print(f"[red]Unexpected error:[/red] {e}")

        raise typer.Exit(code=1)


async def _execute_test(
    parser: str,
    query: str,
    overrides: dict[str, Any],
    timeout: int,
) -> dict:
    """Execute a test request."""
    config = get_config()

    # Convert overrides to options format
    options = [{"id": k, "value": v} for k, v in overrides.items()]

    async with AygaParserHttpClient(config, timeout=timeout) as client:
        result = await client.one_request(
            parser=parser,
            query=query,
            preset="default",
            options=options,
        )
        return result


def _print_test_success(test_results: dict, defaults: Optional[Any], verbose: bool) -> None:
    """Print successful test results."""
    duration = test_results["duration_ms"] / 1000

    console.print(Panel.fit(
        f"[bold green]✓ Test Passed[/bold green]\n"
        f"Parser: [cyan]{test_results['parser']}[/cyan] | "
        f"Duration: [dim]{duration:.1f}s[/dim]",
        border_style="green"
    ))

    # Show step summary
    table = Table(show_header=False, box=None)
    table.add_column("Status", style="bold")
    table.add_column("Step")
    table.add_column("Details", style="dim")

    for step in test_results["steps"]:
        status_icon = {
            "pass": "[green]✓[/green]",
            "fail": "[red]✗[/red]",
            "warning": "[yellow]![/yellow]",
            "info": "[dim]○[/dim]",
        }.get(step["status"], "[dim]○[/dim]")

        step_name = step["name"].replace("_", " ").title()
        message = step["message"]

        # Truncate long messages
        if len(message) > 60 and not verbose:
            message = message[:57] + "..."

        table.add_row(status_icon, step_name, message)

    console.print(table)

    # Show results or API error
    if "api_error" in test_results:
        console.print(f"\n[yellow]Note:[/yellow] API returned an error:")
        console.print(f"  [red]{test_results['api_error']}[/red]")

        if defaults and defaults.notes:
            console.print(f"\n[dim]{defaults.notes}[/dim]")
    else:
        result_count = test_results.get("result_count", 0)
        console.print(f"\n[green]Result:[/green] {result_count} items returned")

        if test_results.get("results"):
            console.print("\n[dim]Sample results:[/dim]")
            for i, item in enumerate(test_results["results"], 1):
                if isinstance(item, dict):
                    preview = str(item)[:100]
                    console.print(f"  {i}. {preview}...")
                else:
                    console.print(f"  {i}. {item}")

    # Show recommendations for test queries
    if test_results["query"] == "test":
        console.print("\n[dim]Note: 'test' queries may return empty results.[/dim]")
        console.print("[dim]This is normal - real queries will return full data.[/dim]")


def _print_test_failure(test_results: dict, defaults: Optional[Any]) -> None:
    """Print test failure results."""
    console.print(Panel.fit(
        f"[bold red]✗ Test Failed[/bold red]\n"
        f"Parser: [cyan]{test_results['parser']}[/cyan]",
        border_style="red"
    ))

    # Show step summary
    table = Table(show_header=False, box=None)
    table.add_column("Status", style="bold")
    table.add_column("Step")
    table.add_column("Details")

    for step in test_results["steps"]:
        status_icon = {
            "pass": "[green]✓[/green]",
            "fail": "[red]✗[/red]",
            "warning": "[yellow]![/yellow]",
            "info": "[dim]○[/dim]",
        }.get(step["status"], "[dim]○[/dim]")

        step_name = step["name"].replace("_", " ").title()
        message = step["message"]

        style = "red" if step["status"] == "fail" else "dim"
        table.add_row(status_icon, step_name, f"[{style}]{message}[/{style}]")

    console.print(table)

    # Show error
    if "error" in test_results:
        console.print(f"\n[bold red]Error:[/bold red] {test_results['error']}")

    # Show recommendations
    console.print("\n[bold]Recommendations:[/bold]")

    # Check if missing overrides
    for step in test_results["steps"]:
        if step["name"] == "validation" and step["status"] == "fail":
            console.print("  1. Add the missing overrides:")
            if defaults:
                for key, value in defaults.default_overrides.items():
                    console.print(f"     --options \"{key}={value}\"")
            console.print(f"\n  2. Or see examples: [cyan]ayga_parser run {test_results['parser']} --examples[/cyan]")

    # Check if proxy error
    if "error" in test_results and "proxy" in test_results["error"].lower():
        console.print("  • This parser requires a proxy configuration")
        console.print("  • Try adding: [cyan]--options \"proxyChecker=reproxy_v4\"[/cyan]")

    # Check if timeout
    if "error" in test_results and "timeout" in test_results["error"].lower():
        console.print("  • Request timed out - try increasing timeout:")
        console.print("    [cyan]--timeout 180[/cyan]")

    console.print()
