# A-Parser CLI (GTV)

**Gateway to External Data** — Modern CLI and MCP server for A-Parser integration.

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
cd projects/aparser-cli
python -m venv .venv
source .venv/bin/activate
pip install -e ".[mcp]"

# Or install MCP support separately
pip install -e ".[mcp]"
```

## 🔧 Configuration

```bash
# Interactive setup
aparser config init

# Or set via environment
export APARSER_HTTP_URL="http://127.0.0.1:9091/API"
export APARSER_REDIS_HOST="127.0.0.1"
export APARSER_REDIS_PORT="6379"
export APARSER_PASSWORD="your_password"
```

- Config files, presets, and manifest cache now share one canonical config directory:
  - Windows: `%APPDATA%\aparser-cli`
  - macOS: `~/Library/Application Support/aparser-cli`
  - Linux: `~/.config/aparser-cli`
- HTTP requests can use both the API password payload and HTTP Basic Auth. Set `APARSER_HTTP_BASIC_USERNAME` and optionally `APARSER_HTTP_BASIC_PASSWORD` if your backend requires explicit Basic Auth credentials.

## 🖥️ CLI Usage

### Basic Commands

```bash
# Test connection
aparser ping

# List available parsers
aparser parsers list
aparser parsers list --category SE

# Get parser details
aparser parsers info SE::Google

# Submit job to Redis queue
aparser redis push SE::Google "test query" --preset default

# Wait for result
aparser redis wait aparser_result_abc123 --timeout 300
```

### Advanced Usage

```bash
# Batch processing from file
aparser redis push SE::Google --file queries.txt --async

# Custom result queue
aparser redis push Net::Whois "example.com" --result-queue my_results

# Passthrough JSON for complex options
aparser redis push SE::Google "query" --from-json '{
  "options": [
    {"id": "pagecount", "value": 5, "type": "override"}
  ]
}'

# HTTP fallback (synchronous)
aparser http request SE::Google "query" --preset default
```

## 🤖 MCP Server

Run the MCP server for AI agent integration:

```bash
# Start MCP server
aparser-mcp

# Or via Python
python -m aparser_cli.mcp.server
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
# Returns: {"status": "queued", "job_id": "aparser_result_abc123"}

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
           │  A-Parser CLI │       │
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
           │  A-Parser   │            │
           │   Engine    │            │
           └─────────────┘            │
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=aparser_cli --cov-report=html

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

- **A-Parser**: https://a-parser.com/
- **Typer**: https://typer.tiangolo.com/
- **MCP**: https://modelcontextprotocol.io/

---

**Built with ❤️ by Gubin 🤖 for AYGA**
