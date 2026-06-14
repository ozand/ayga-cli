"""Dry-run utilities for previewing API calls without execution.

Provides functionality to preview execution plans and validate payloads
before sending to ayga_parser API.
"""

from __future__ import annotations

import json
from typing import Any, Optional
from uuid import uuid4

from rich.console import Console
from rich.json import JSON as RichJSON
from rich.panel import Panel
from rich.table import Table

console = Console()


class DryRunSimulator:
    """Simulates API execution for dry-run mode.

    Builds preview of what would be executed without making actual API calls.

    Attributes:
        parser: Parser name
        query: Query string
        preset: Preset name
        options: Parser options
        transport: Transport method (redis or http)
    """

    def __init__(
        self,
        parser: str,
        query: str,
        preset: str = "default",
        options: Optional[list[dict]] = None,
        transport: str = "http",
        config: Optional[Any] = None,
    ):
        self.parser = parser
        self.query = query
        self.preset = preset
        self.options = options or []
        self.transport = transport
        self.config = config
        self.result_queue = f"ayga_parser_result_{uuid4().hex[:8]}"

    def build_payload(self) -> dict[str, Any]:
        """Build the actual API payload that would be sent.

        Returns:
            Complete API payload dictionary
        """
        # Mask password for display
        password = "***"
        if self.config and hasattr(self.config, 'get_password'):
            pwd = self.config.get_password()
            if pwd:
                password = "*" * len(pwd)

        data: dict[str, Any] = {
            "parser": self.parser,
            "preset": self.preset,
            "query": self.query,
        }

        if self.options:
            data["options"] = self.options

        return {
            "password": password,
            "action": "oneRequest",
            "data": data,
        }

    def estimate_time(self) -> str:
        """Estimate execution time based on parser and options.

        Returns:
            Human-readable time estimate
        """
        # Base estimates by parser category
        base_times = {
            "SE::": "5-15 seconds",
            "FreeAI::": "10-30 seconds",
            "Net::": "3-10 seconds",
            "HTML::": "2-5 seconds",
        }

        # Check for pagination
        has_pagination = any(
            opt.get("id") in ["pagecount", "pages", "max_pages"]
            for opt in self.options
        )

        base_time = "5-10 seconds"
        for prefix, estimate in base_times.items():
            if self.parser.startswith(prefix):
                base_time = estimate
                break

        if has_pagination:
            base_time += " (per page)"

        return base_time

    def get_transport_details(self) -> dict[str, Any]:
        """Get transport-specific details.

        Returns:
            Dictionary with transport configuration
        """
        if self.transport == "redis":
            return {
                "type": "redis",
                "queue": "ayga_parser_redis_api",
                "result_queue": self.result_queue,
                "pattern": "LPUSH request -> BLPOP result",
            }
        else:
            return {
                "type": "http",
                "endpoint": "/API",
                "method": "POST",
                "synchronous": True,
            }

    def generate_preview(self) -> dict[str, Any]:
        """Generate complete dry-run preview.

        Returns:
            Preview dictionary with execution plan
        """
        return {
            "dry_run": True,
            "execution_plan": {
                "parser": self.parser,
                "query": self.query,
                "preset": self.preset,
                "options": self._options_to_dict(),
                "transport": self.transport,
                "queue": "ayga_parser_redis_api" if self.transport == "redis" else None,
                "result_queue": self.result_queue if self.transport == "redis" else None,
                "estimated_time": self.estimate_time(),
                "api_payload": self.build_payload(),
            },
        }

    def _options_to_dict(self) -> dict[str, Any]:
        """Convert options list to dictionary for display."""
        result = {}
        for opt in self.options:
            if "id" in opt and "value" in opt:
                result[opt["id"]] = opt["value"]
        return result

    def print_preview(self) -> None:
        """Print formatted preview to console."""
        preview = self.generate_preview()
        plan = preview["execution_plan"]

        # Title panel
        console.print(Panel.fit(
            "[bold yellow]DRY RUN MODE[/bold yellow]\n"
            "Showing what would be executed (no actual API call)",
            border_style="yellow"
        ))

        # Execution plan table
        table = Table(title="Execution Plan", show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Parser", plan["parser"])
        table.add_row("Query", plan["query"])
        table.add_row("Preset", plan["preset"])

        if plan["options"]:
            options_str = json.dumps(plan["options"], indent=2)
            table.add_row("Options", options_str)

        table.add_row("Transport", plan["transport"])

        if plan["queue"]:
            table.add_row("Queue", plan["queue"])
        if plan["result_queue"]:
            table.add_row("Result Queue", plan["result_queue"])

        table.add_row("Est. Time", f"[italic]{plan['estimated_time']}[/italic]")

        console.print(table)

        # API Payload
        console.print("\n[bold]API Payload:[/bold]")
        payload_json = json.dumps(plan["api_payload"], indent=2, ensure_ascii=False)
        console.print(RichJSON(payload_json))

        console.print("\n[dim]Use without --dry-run to execute[/dim]")


def print_dry_run_summary(
    parser: str,
    query: str,
    preset: str = "default",
    options: Optional[list[dict]] = None,
    transport: str = "http",
    config: Optional[Any] = None,
) -> dict[str, Any]:
    """Quick function to print dry-run summary.

    Args:
        parser: Parser name
        query: Query string
        preset: Preset name
        options: Parser options
        transport: Transport method
        config: Configuration object

    Returns:
        Preview dictionary
    """
    simulator = DryRunSimulator(
        parser=parser,
        query=query,
        preset=preset,
        options=options,
        transport=transport,
        config=config,
    )
    simulator.print_preview()
    return simulator.generate_preview()
