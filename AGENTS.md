# AGENTS.md — ayga-cli

## Required reading
- `CONTEXT.md` — Critical Rules of Engagement, exit codes, and output formatting specifically targeted at AI agents orchestrating data access workflows. **Read this file before generating CLI calls.**
- `README.md` — General usage documentation, setup, and features.
- `pyproject.toml` — Project packaging configuration, dependencies (`typer`, `redis`, `pydantic`, `html2text`, etc.), and CLI entry points.

## Project overview
`ayga-cli` (formerly `aparser-cli`) is a command-line data access client designed to fetch data from configured sources via the `redis_wrapper` backend. It handles dual transport (Redis + HTTP), features an MCP server implementation, and provides helper commands for AI data pipelines.
**Core principle**: You do not need to configure or know about parsers directly; query standard sources via `ayga_parser get <source> <query>`.

## File structure
- `src/ayga_cli/main.py` — Entry point of the CLI application using Typer.
- `src/ayga_cli/mcp_server.py` — Handles MCP protocol tool declarations.
- `src/ayga_cli/client/` — Implementations for the Redis and HTTP transports.
- `tests/` — Comprehensive test suite with pytest.

## Environment setup
Install packages in edit mode with dev and mcp dependencies:
```bash
pip install -e ".[dev,mcp]"
```

Configure backend connections using environment variables:
```bash
export ayga-parser_HTTP_URL="http://127.0.0.1:9091/API"
export ayga-parser_REDIS_HOST="127.0.0.1"
export ayga-parser_REDIS_PORT="6379"
export ayga-parser_PASSWORD="your_password"
```

## How to run
Check available sources:
```bash
ayga_parser sources list
```

Fetch data from a source (always use `--fields` to limit response payload sizes during agent orchestration):
```bash
ayga_parser get web-search "climate change 2025" --fields title,url,snippet
```

## Build and test commands
Run pytest suite:
```bash
pytest tests/ -v
```

Run code quality checks (Ruff & Mypy):
```bash
ruff check src/
mypy src/
```

## Tech stack conventions
- **Typer & Rich**: Typer handles CLI commands; Rich formats the console output beautifully.
- **Exit Codes**: As defined in `CONTEXT.md`, handle exit codes properly (0: Success, 1: General error, 2: Timeout, 3: Source not found, 4: Server unavailable, 5: Invalid input).

## Security considerations
- Store passwords securely; the CLI integrates with OS keyrings.
- Never output full raw HTML in logs; rely on the `--fields` argument to pull exactly what is needed for downstream LLM parsing.
