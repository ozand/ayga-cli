# ayga-cli

**Data access client** — fetch data from configured sources via a Redis Wrapper server. For humans, AI agents, and automation scripts.

> **For AI Agents:** Read [CONTEXT.md](./CONTEXT.md) first — it contains Rules of Engagement, output format, exit codes, and usage examples optimised for LLM consumption. There's also a [SKILL.md](./SKILL.md) for skill-based agent frameworks.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Philosophy

You ask for data by **source name** and **query** — the server handles parsers, proxies, and infrastructure. You do not need to know what runs behind the source, and the CLI never exposes that detail: no parser names, no proxy configuration, no backend engine branding in the interface.

## Features

- **Source-based interface**: `get <source> <query>` — no backend/parser knowledge required
- **Redis transport**: async queue-based communication with the backend server
- **MCP server**: 2-tool MCP server (`fetch_data`, `list_sources`) for AI agent integration
- **Modern CLI**: Typer + Rich for readable output, `--json`/`--stream` for machine consumption
- **Secure**: OS keyring for password storage
- **Tested**: 195 passing tests (5 skipped)

## Installation

```bash
# Clone and install
cd ayga-cli
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[mcp]"
```

The `[mcp]` extra is only needed if you plan to run the MCP server (`ayga_parser-mcp`).

## Authentication

`ayga-cli` talks to a hosted backend — you need an API key (`AYGA_PASSWORD`) to use it. Get your API key from https://redis.ayga.tech or contact support@ayga.tech.

## Configuration

```bash
# Interactive setup
ayga_parser config init

# Or set via environment variables (AYGA_ prefix, case-insensitive)
export AYGA_HTTP_URL="http://127.0.0.1:9091/API"
export AYGA_REDIS_HOST="127.0.0.1"
export AYGA_REDIS_PORT="6379"
export AYGA_PASSWORD="your_password"
```

- Config files, presets, and manifest cache share one canonical config directory:
  - Windows: `%APPDATA%\ayga-cli`
  - macOS: `~/Library/Application Support/ayga-cli`
  - Linux: `~/.config/ayga-cli`
- Settings can also be dropped into a `.env` file inside that config directory — it's loaded automatically.
- HTTP requests can use both the API password payload and HTTP Basic Auth. Set `AYGA_HTTP_BASIC_USERNAME` and optionally `AYGA_HTTP_BASIC_PASSWORD` if your backend requires explicit Basic Auth credentials.
- View the resolved configuration at any time with `ayga_parser config show`.

## CLI Usage

### Quick start — the `get`/`sources` interface

This is the primary, backend-agnostic interface. Discover what's available, then fetch data by source name:

```bash
# 1. See what data sources are configured on this server
ayga_parser sources list

# 2. Inspect a source's schema (fields, description, examples) before using it
ayga_parser sources info web-search

# 3. Fetch data
ayga_parser get web-search "machine learning 2025"

# 4. Limit the response to specific fields (recommended for agent contexts)
ayga_parser get web-search "machine learning 2025" --fields title,url,snippet

# 5. Stream results as NDJSON — one record per line
ayga_parser get web-search "Python tutorials" --stream --fields title,url

# 6. Get structured JSON output
ayga_parser get ai-answer "What is quantum computing?" --json

# 7. Preview what would be sent, without executing
ayga_parser get web-search "test" --dry-run

# 8. Custom timeout (default: 300s)
ayga_parser get ai-answer "explain entropy" --timeout 120
```

`sources list` and `sources info` cache results locally; pass `--no-cache` to force a fresh fetch from the server.

### Helper commands (`+verb`)

For multi-step operations that combine more than one source call. Each `+verb` is a command group with a single subcommand of the same name:

```bash
# Fetch a URL and return clean Markdown (uses the 'article' source internally)
ayga_parser +extract extract https://example.com/article

# Combine web-search + ai-answer for a topic
ayga_parser +research research "quantum computing"
```

Use a helper only when a single `get` call isn't enough — if one source covers it, call `get` directly.

### Connectivity and diagnostics

```bash
# Test HTTP connectivity to the configured backend
ayga_parser ping

# Show the resolved configuration
ayga_parser config show
```

### Lower-level parser/preset management

`ayga-cli` also ships lower-level command groups (`parsers`, `presets`) for managing the underlying parser manifest and reusable option presets. These are for operators configuring the backend, not for the day-to-day `get`/`sources` workflow described above:

```bash
ayga_parser parsers list
ayga_parser parsers list --category SE
ayga_parser presets list
```

See `ayga_parser parsers --help` and `ayga_parser presets --help` for details.

## Exit Codes

Machine consumers should check the exit code rather than assuming success:

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success — data in stdout | Parse stdout as JSON |
| 1 | General/unknown error | Check stderr |
| 2 | Timeout — server did not respond in time | Retry or increase `--timeout` |
| 3 | Source not found | Run `sources list` to see available sources |
| 4 | Server unavailable — Redis Wrapper unreachable | Report infrastructure issue, do not retry in a loop |
| 5 | Invalid input — bad source name or empty query | Fix the input |

Error details are always written to **stderr**; stdout is reserved for clean data output.

## MCP Server

Run the MCP server for AI agent integration:

```bash
# Start MCP server (requires the [mcp] extra)
ayga_parser-mcp

# Or via Python
python -m ayga_cli.mcp.server
```

### MCP Tools

| Tool | Purpose |
|------|---------|
| `list_sources()` | List available data sources |
| `fetch_data(source, query, timeout=300)` | Fetch data from a named source |

### Example MCP usage

```python
# Discover available sources
sources = await mcp.list_sources()

# Fetch data from a source
result = await mcp.fetch_data(source="web-search", query="machine learning 2025")
# Returns: {"success": true, "status": "completed", "result": {...}}
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Human     │     │  AI Agent   │     │    Cron     │
│   (CLI)     │     │   (MCP)     │     │   (Job)     │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────┬───────┴───────────────────┘
                    │
            ┌───────▼────────┐
            │   ayga-cli      │
            │  ├─ get/sources │
            │  ├─ Redis Client│
            │  └─ MCP Server  │
            └───────┬─────────┘
                    │
            ┌───────▼────────┐
            │  Redis Wrapper │
            │   (backend)    │
            └────────────────┘
```

`ayga-cli` only talks to the Redis Wrapper server. What the server does internally (parsers, proxies, presets) is its own concern — not something callers of `get`/`sources` need to know.

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=ayga_cli --cov-report=html

# Specific test file
pytest tests/test_commands/test_get.py -v
```

Current status: **195 passed, 5 skipped**.

## License

MIT License — see the `license` field in [pyproject.toml](pyproject.toml).

## Credits

- **Typer**: https://typer.tiangolo.com/
- **MCP**: https://modelcontextprotocol.io/

---

**Built for AYGA**
