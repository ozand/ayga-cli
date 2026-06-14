# ayga-parser CLI (GTV)

**Gateway to External Data** — Modern CLI and MCP server for ayga-parser integration.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Features

- **Dual Transport**: Redis (primary, async) + HTTP (fallback, sync)
- **MCP Integration**: 2-tool MCP server for AI agents (avoids "Instruction Manual Tax")
- **Modern CLI**: Typer + Rich for beautiful output
- **Secure**: OS keyring for password storage
- **Tested**: 107 tests, 77% coverage

## 📦 Installation

```bash
# Clone and install
cd projects/ayga-cli
python -m venv .venv
source .venv/bin/activate
pip install -e ".[mcp]"

# Or install MCP support separately
pip install -e ".[mcp]"
```

## 🔧 Configuration

```bash
# Interactive setup
ayga-parser config init

# Or set via environment
export ayga-parser_HTTP_URL="http://127.0.0.1:9091/API"
export ayga-parser_REDIS_HOST="127.0.0.1"
export ayga-parser_REDIS_PORT="6379"
export ayga-parser_PASSWORD="your_password"
```

- Config files, presets, and manifest cache now share one canonical config directory:
  - Windows: `%APPDATA%\ayga-cli`
  - macOS: `~/Library/Application Support/ayga-cli`
  - Linux: `~/.config/ayga-cli`
- HTTP requests can use both the API password payload and HTTP Basic Auth. Set `ayga-parser_HTTP_BASIC_USERNAME` and optionally `ayga-parser_HTTP_BASIC_PASSWORD` if your backend requires explicit Basic Auth credentials.

## 🖥️ CLI Usage

### Basic Commands

```bash
# Test connection
ayga-parser ping

# List available parsers
ayga-parser parsers list
ayga-parser parsers list --category SE

# Get parser details
ayga-parser parsers info SE::Google

# Submit job to Redis queue
ayga-parser redis push SE::Google "test query" --preset default

# Wait for result
ayga-parser redis wait ayga-parser_result_abc123 --timeout 300
```

### Advanced Usage

```bash
# Batch processing from file
ayga-parser redis push SE::Google --file queries.txt --async

# Custom result queue
ayga-parser redis push Net::Whois "example.com" --result-queue my_results

# Passthrough JSON for complex options
ayga-parser redis push SE::Google "query" --from-json '{
  "options": [
    {"id": "pagecount", "value": 5, "type": "override"}
  ]
}'

# HTTP fallback (synchronous)
ayga-parser http request SE::Google "query" --preset default
```

## 🤖 MCP Server

Run the MCP server for AI agent integration:

```bash
# Start MCP server
ayga-parser-mcp

# Or via Python
python -m ayga_cli.mcp.server
```

### MCP Tools

| Tool | Purpose |
|------|---------|
| `search_parsers(query, category)` | Discover parsers (lightweight, no schemas) |
| `run_parser(parser, query, async_mode, ...)` | Execute parsing job |

### Example MCP Usage

```python
# AI agent calls MCP tool
result = await mcp.run_parser(
    parser="SE::Google",
    query="test",
    async_mode=True  # Returns immediately with job_id
)
# Returns: {"status": "queued", "job_id": "ayga-parser_result_abc123"}

# Later, check result
result = await mcp.run_parser(
    parser="SE::Google", 
    query="test",
    async_mode=False  # Blocks until complete
)
```

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Human     │     │  AI Agent   │     │    Cron     │
│   (CLI)     │     │   (MCP)     │     │   (Job)     │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────┬───────┴───────┬───────────┘
                   │               │
           ┌───────▼───────┐       │
           │  ayga-parser CLI │       │
           │  ├─ HTTP Client     │
           │  ├─ Redis Client    │
           │  └─ MCP Server      │
           └───────┬───────────┘       │
                   │                   │
       ┌───────────┴───────────┐       │
       │                       │       │
┌──────▼──────┐      ┌────────▼──────┐│
│    HTTP     │      │     Redis     ││
│   :9091     │      │    :6379      ││
└──────┬──────┘      └────────┬──────┘│
       │                      │       │
       └──────────┬───────────┘       │
                  │                   │
           ┌──────▼──────┐            │
           │  ayga-parser   │            │
           │   Engine    │            │
           └─────────────┘            │
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=ayga_cli --cov-report=html

# Specific test file
pytest tests/test_http_client.py -v
```

## 📊 Project Status

| Phase | Status | Progress |
|-------|--------|----------|
| Core CLI | ✅ Done | 100% |
| HTTP Client | ✅ Done | 17 methods |
| Redis Client | ✅ Done | LPUSH/BLPOP |
| MCP Server | ✅ Done | 2 tools |
| Tests | ✅ Done | 107 tests |
| Documentation | ✅ Done | This README |

## 📝 License

MIT License — see [LICENSE](LICENSE) file.

## 🙏 Credits

- **ayga-parser**: https://ayga-parser.com/
- **Typer**: https://typer.tiangolo.com/
- **MCP**: https://modelcontextprotocol.io/

---

**Built with ❤️ by Gubin 🤖 for AYGA**
