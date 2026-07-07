# System Architecture v2.0
# ayga-parser CLI & AYGA MCP Integration

**Date:** 2026-03-07 (Revised after ayga-parser API analysis)  
**Status:** Design Complete

---

## 1. Executive Summary

After analyzing the ayga-parser API documentation and reference implementations (Google Workspace CLI, CLIHub, MCP CLI), the architecture has been **significantly revised** to align with ayga-parser's actual capabilities and best practices for agentic tool use.

**Key Changes from v1.0:**
- **Lazy Tool Loading:** Only 2 MCP tools exposed (`search_parsers`, `run_parser`) instead of 100+
- **Redis-First Design:** HTTP API is secondary; Redis queue is primary for production
- **Unified Queue:** Single `ayga-parser_redis_api` queue with configurable result queues
- **Passthrough JSON:** `--from-json` flag for complex preset overrides

---

## 2. ayga-parser API Capabilities (Analyzed)

### 2.1 HTTP API Methods

| Method | Purpose | Use Case |
|--------|---------|----------|
| `ping` | Health check | CLI startup verification |
| `oneRequest` | Single sync parsing | Quick queries, debugging |
| `bulkRequest` | Batch sync parsing | Small batches (<100 queries) |
| `getParserInfo` | Get parser metadata | Dynamic tool discovery |
| `getParsersList` | List all parsers | MCP tool enumeration |
| `getTasksList` | Active tasks monitoring | Queue depth metrics |

### 2.2 Redis API (Primary Transport)

**Queue Structure:**
```
LPUSH ayga-parser_redis_api {request_json}
→ ayga-parser processes
→ LPUSH {result_queue} {result_json}
← BLPOP {result_queue} {timeout}
```

**Key Features:**
- **Async by default:** LPUSH returns immediately
- **Blocking retrieval:** BLPOP with timeout
- **Multiple parsers:** Can connect N ayga-parser instances to same queue
- **Auto-expire:** TTL on results (default 3600s)
- **Separate result queues:** Configurable per-request

### 2.3 Parser Configuration

**Override System:**
```json
{
  "options": [
    {"id": "pagecount", "value": 1, "type": "override"},
    {"id": "linksperpage", "value": 10, "type": "override"}
  ]
}
```

**Presets:** Named configurations stored in ayga-parser
**ConfigPresets:** Thread pool configurations (concurrency settings)

---

## 3. Revised Architecture

### 3.1 High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACES                          │
├─────────────────────────────────────────────────────────────┤
│  Human Engineer          │  AI Agent (Claude/Gubin)         │
│  ↓                       │  ↓                               │
│  Typer CLI               │  AYGA MCP Server                 │
│  (Interactive)           │  (2 tools only)                  │
└──────────┬───────────────┴──────────┬───────────────────────┘
           │                          │
           └──────────┬───────────────┘
                      │
           ┌──────────▼───────────────┐
           │    ayga-parser CLI Core     │
           │  ┌─────────────────────┐ │
           │  │  Transport Router   │ │
           │  │  • Redis (primary)  │ │
           │  │  • HTTP (fallback)  │ │
           │  └─────────────────────┘ │
           │  ┌─────────────────────┐ │
           │  │  Config Manager     │ │
           │  │  • Pydantic Settings│ │
           │  │  • OS Keyring auth  │ │
           │  └─────────────────────┘ │
           └──────────┬───────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌────▼─────┐ ┌────▼──────────┐
│   Redis      │ │   HTTP   │ │   Backend     │
│   Queue      │ │   API    │ │   Instance(s) │
│              │ │          │ │               │
│ ayga-parser_     │ │:9091/API │ │  • 100 threads│
│ redis_api    │ │          │ │  • Multiple   │
│              │ │          │ │    presets    │
└──────────────┘ └──────────┘ └───────────────┘
```

### 3.2 Transport Layer

**Primary: Redis**
```python
# Producer (CLI/MCP)
redis.lpush("ayga-parser_redis_api", json.dumps({
    "password": "...",
    "action": "oneRequest",
    "data": {
        "parser": "SE::Google",
        "preset": "default",
        "query": "test",
        "resultQueue": "ayga_results_123"  # Custom queue
    }
}))

# Consumer (CLI/MCP)
result = redis.blpop("ayga_results_123", timeout=300)
```

**Fallback: HTTP**
```python
# Direct sync request
httpx.post("http://127.0.0.1:9091/API", json={
    "password": "...",
    "action": "oneRequest",
    "data": {...}
})
```

### 3.3 MCP Server Design (Revised)

**Only 2 Tools Exposed:**

```python
@mcp.tool()
async def search_parsers(
    query: str = "",  # Optional filter
    category: str = ""  # Optional category filter
) -> list[dict]:
    """
    Search available ayga-parser parsers and presets.
    Returns lightweight metadata (name, description, category).
    Does NOT return full JSON schemas (saves tokens).
    """
    pass

@mcp.tool()
async def run_parser(
    parser: str,  # e.g., "SE::Google"
    query: str,
    preset: str = "default",
    config_preset: str = "default",
    options: dict = None,  # Override preset params
    async_mode: bool = True,  # Return job_id or wait
    timeout: int = 300
) -> dict:
    """
    Execute parsing job via ayga-parser.
    
    Mode 1 (async_mode=True): Returns immediately with job_id
    Mode 2 (async_mode=False): Blocks until result, returns data
    
    For complex overrides, use options={"from_json": {...}}
    """
    pass
```

**Why only 2 tools?**
- Avoids "Instruction Manual Tax" (~15k tokens for 100+ tools)
- CLI discovery via `--help` uses ~900 tokens
- Dynamic discovery via `search_parsers` on-demand

---

## 4. CLI Command Structure

### 4.1 Core Commands

```bash
# Configuration
ayga-parser config init                    # Interactive setup
ayga-parser config set redis.host 127.0.0.1
ayga-parser config auth                    # Store password in OS keyring

# Discovery
ayga-parser parsers list                   # All parsers
ayga-parser parsers list --category SE     # Filter by category
ayga-parser parsers info SE::Google        # Detailed parser info

# Redis Operations (Primary)
ayga-parser redis push SE::Google "query" --preset default
ayga-parser redis push SE::Google --file queries.txt --async
ayga-parser redis wait ayga_results_123 --timeout 300
ayga-parser redis consume ayga_results --continuous

# HTTP Operations (Fallback)
ayga-parser http request SE::Google "query" --preset default

# Task Management
ayga-parser task status {job_id}
ayga-parser task list --active
ayga-parser task cancel {job_id}

# Pipeline Mode
ayga-parser pipeline produce --input domains.txt --parser Net::Whois
ayga-parser pipeline consume --output results.jsonl
```

### 4.2 Advanced Features

**Passthrough JSON:**
```bash
# Instead of complex CLI flags, pass raw JSON
ayga-parser redis push SE::Google "query" --from-json '{
  "options": [
    {"id": "pagecount", "value": 5, "type": "override"}
  ]
}'
```

**Pagination Handling:**
```bash
# CLI handles pagination automatically
ayga-parser http request SE::Google "query" --page-all
```

**Multiple Output Formats:**
```bash
ayga-parser redis wait {queue} --format json    # Structured JSON
ayga-parser redis wait {queue} --format jsonl   # NDJSON for streaming
ayga-parser redis wait {queue} --format table   # Human-readable table
ayga-parser redis wait {queue} --format csv     # CSV export
```

---

## 5. Configuration Management

### 5.1 Config Sources (Priority Order)

1. **Environment Variables:** `ayga-parser_REDIS_HOST`, `ayga-parser_PASSWORD`
2. **Config File:** `~/.config/ayga-cli/config.yaml`
3. **OS Keyring:** Secure password storage
4. **CLI Flags:** `--redis-host`, `--password`

### 5.2 Config Schema (Pydantic)

```python
class ayga-parserConfig(BaseSettings):
    # HTTP API
    http_url: str = "http://127.0.0.1:9091/API"
    
    # Redis
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_queue: str = "ayga-parser_redis_api"
    redis_password: Optional[str] = None
    
    # Auth
    password: SecretStr  # From keyring or env
    
    # Defaults
    default_timeout: int = 300
    default_preset: str = "default"
    default_config_preset: str = "default"
    
    class Config:
        env_prefix = "ayga-parser_"
        secrets_dir = "/run/secrets"  # Docker support
```

---

## 6. Security Architecture

### 6.1 Authentication Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │────▶│  OS Keyring │────▶│   CLI       │
│   (once)    │     │  (secure)   │     │   (runtime) │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                       ┌────────────────────────┘
                       │
                ┌──────▼──────┐
                │  Backend    │
                │  Password   │
                │  (in-mem)   │
                └──────┬──────┘
                       │
                ┌──────▼──────┐
                │  Redis/HTTP │
                │  Request    │
                └─────────────┘
```

### 6.2 Security Best Practices

- **Never store password in config files** (use OS keyring)
- **Redis auth:** Support Redis AUTH if configured
- **TLS:** Support rediss:// for Redis over TLS
- **Input validation:** Pydantic models for all inputs
- **Secrets masking:** Passwords redacted in logs

---

## 7. Error Handling & Resilience

### 7.1 Retry Strategy

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((RedisError, HTTPError))
)
async def execute_request(request: dict) -> dict:
    pass
```

### 7.2 Fallback Chain

1. **Redis LPUSH** → Success
2. **Redis LPUSH** → Retry × 2 → Fail
3. **HTTP oneRequest** → Success
4. **HTTP oneRequest** → Retry × 2 → Fail
5. **Error to user** with detailed context

### 7.3 Graceful Degradation

- Redis unavailable → Auto-switch to HTTP
- Parser timeout → Return partial results + timeout flag
- Queue overflow → Backpressure (reject new requests)

---

## 8. Monitoring & Observability

### 8.1 Metrics

```python
# Prometheus-style metrics
ayga-parser_requests_total{transport="redis", status="success"}
ayga-parser_requests_total{transport="http", status="error"}
ayga-parser_queue_depth{queue="ayga-parser_redis_api"}
ayga-parser_request_duration_seconds{quantile="0.95"}
```

### 8.2 Logging

```python
# Structured JSON logging
{
    "timestamp": "2026-03-07T12:00:00Z",
    "level": "INFO",
    "component": "redis_client",
    "action": "lpush",
    "parser": "SE::Google",
    "queue": "ayga-parser_redis_api",
    "duration_ms": 5.2
}
```

---

## 9. Integration Patterns

### 9.1 AYGA MCP Integration

```python
# MCP Server initialization
mcp = MCP("ayga-parser-mcp")

@mcp.tool()
async def search_parsers(query: str = "") -> list[dict]:
    """Lightweight parser discovery"""
    cli = ayga-parserCLI()
    return await cli.parsers.search(query)

@mcp.tool()
async def run_parser(
    parser: str,
    query: str,
    preset: str = "default",
    async_mode: bool = True
) -> dict:
    """Execute parsing job"""
    cli = ayga-parserCLI()
    
    if async_mode:
        job_id = await cli.redis.push(parser, query, preset)
        return {"status": "queued", "job_id": job_id}
    else:
        result = await cli.redis.wait_for_result(parser, query, preset)
        return result
```

### 9.2 Cron Job Integration

```bash
#!/bin/bash
# Daily domain parsing
ayga-parser redis push Net::Whois \
    --file /data/domains.txt \
    --preset "default" \
    --output-queue daily_whois_results \
    --async

# Process results
ayga-parser redis consume daily_whois_results \
    --format jsonl \
    --output /data/results.jsonl
```

---

## 10. Deployment Options

### 10.1 Local Development

```bash
pip install ayga-cli
ayga-parser config init
ayga-parser ping
```

### 10.2 Docker

```dockerfile
FROM python:3.12-slim
RUN pip install ayga-cli
ENTRYPOINT ["ayga-parser"]
```

### 10.3 Systemd Service

```ini
[Unit]
Description=ayga-parser CLI MCP Server
After=network.target

[Service]
Type=simple
User=ayga-parser
ExecStart=/usr/local/bin/ayga-parser mcp serve
Restart=always
Environment=ayga-parser_REDIS_HOST=127.0.0.1

[Install]
WantedBy=multi-user.target
```

---

## 11. Comparison with Reference Implementations

| Feature | Google CLI | CLIHub | MCP CLI | ayga-parser CLI (This) |
|---------|------------|--------|---------|---------------------|
| Dynamic commands | ✅ Discovery API | ✅ MCP codegen | ❌ Static | ✅ Parser introspection |
| Redis transport | ❌ | ❌ | ❌ | ✅ Primary |
| HTTP fallback | ✅ | ✅ | ✅ | ✅ Secondary |
| OS Keyring | ✅ | ✅ | ❌ | ✅ |
| MCP integration | ❌ | ✅ | ✅ | ✅ 2 tools only |
| Static binary | ❌ | ✅ | ❌ | ❌ Python |
| Passthrough JSON | ❌ | ✅ | ❌ | ✅ |
| Pagination auto | ✅ | ❌ | ❌ | ✅ `--page-all` |

---

## 12. Implementation Roadmap

### Phase 1: Core (Week 1)
- [ ] Project scaffold (Typer, Pydantic, pytest)
- [ ] Config management (env, file, keyring)
- [ ] HTTP client (all 17 methods)
- [ ] Redis client (LPUSH, BLPOP)
- [ ] Basic CLI: `ping`, `parsers list`, `redis push`

### Phase 2: Advanced (Week 2)
- [ ] Passthrough JSON (`--from-json`)
- [ ] Pagination handling (`--page-all`)
- [ ] Pipeline mode (produce/consume)
- [ ] Multiple output formats (json, jsonl, table, csv)
- [ ] Task management (status, cancel, list)

### Phase 3: MCP (Week 3)
- [ ] MCP server scaffold
- [ ] `search_parsers` tool
- [ ] `run_parser` tool (sync/async modes)
- [ ] AYGA integration testing

### Phase 4: Polish (Week 4)
- [ ] Zero-Trust QA (automated tests)
- [ ] Documentation (README, examples)
- [ ] Docker image
- [ ] Systemd service files

---

**Document Owner:** Gubin 🤖  
**Reviewers:** Ozand  
**Last Updated:** 2026-03-07
