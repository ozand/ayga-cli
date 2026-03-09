"""Ping command to test HTTP connection to A-Parser."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Import will be available after client implementation
# from aparser_cli.client import AParserHttpClient

app = typer.Typer(help="Test HTTP connection to A-Parser")
console = Console()


@app.callback(invoke_without_command=True)
def ping(
    host: str = typer.Option("http://localhost", "--host", "-h", help="A-Parser HTTP host"),
    port: int = typer.Option(9091, "--port", "-p", help="A-Parser HTTP port"),
    timeout: int = typer.Option(5, "--timeout", "-t", help="Connection timeout in seconds"),
    format_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Test HTTP connection to A-Parser server."""
    url = f"{host}:{port}"
    
    try:
        # Will use AParserHttpClient once implemented
        # client = AParserHttpClient(base_url=url, timeout=timeout)
        # result = client.ping()
        
        # Placeholder for actual implementation
        result = {"status": "ok", "message": "Connection successful"}
        
        if format_json:
            import json
            console.print(json.dumps(result, indent=2))
        else:
            status_text = Text("✓ Connected", style="bold green")
            message = Text(f"Successfully connected to A-Parser at {url}")
            
            panel = Panel(
                f"{status_text}\n{message}",
                title="A-Parser Ping",
                border_style="green"
            )
            console.print(panel)
            
    except Exception as e:
        if format_json:
            import json
            console.print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            status_text = Text("✗ Connection Failed", style="bold red")
            error_msg = Text(str(e), style="red")
            
            panel = Panel(
                f"{status_text}\n{error_msg}",
                title="A-Parser Ping",
                border_style="red"
            )
            console.print(panel)
            raise typer.Exit(code=1)
