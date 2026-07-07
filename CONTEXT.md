# ayga-cli Context — For AI Agents

`ayga-cli` is a **data access client**. It fetches data from configured sources via a Redis Wrapper server. You ask for data by source name and query — the server handles the rest.

> You do NOT need to know about parsers, proxies, or infrastructure. That is the server's concern.

---

## Rules of Engagement

**1. Discover sources first**
Always run `ayga_parser sources list` before your first `get` call to see what sources are available on this server. Available sources depend on server configuration — there is no hardcoded list.

**2. Protect your context window**
Use `--fields` to limit response size. Sources can return large payloads (full articles, many search results). Request only what you need:
```
ayga_parser get google_search "query" --fields title,url,snippet
```

**3. Handle exit codes explicitly**
Do not assume success. Always check the exit code:
```
0 — Success. Result is in stdout as JSON.
1 — General/unknown error.
2 — Timeout. Server did not respond in time. Retry or increase --timeout.
3 — Source not found. Use 'sources list' to see available sources.
4 — Server unavailable. Redis Wrapper is unreachable.
5 — Invalid input. Check your source name and query format.
```

---

## Core Syntax

```bash
# See what data sources are available
ayga_parser sources list

# Get info about a specific source (schema, fields, examples)
ayga_parser sources info <source-name>

# Fetch data from a source
ayga_parser get <source> <query>

# Fetch with field filtering (recommended in agent contexts)
ayga_parser get <source> <query> --fields field1,field2

# Fetch as NDJSON stream (one record per line, good for lists)
ayga_parser get <source> <query> --stream

# Inspect what would be sent without executing (debug)
ayga_parser get <source> <query> --dry-run

# Set custom timeout (default: 300s)
ayga_parser get <source> <query> --timeout 60

# Get structured JSON output
ayga_parser get <source> <query> --json
```

---

## Output Format

Successful responses (`exit 0`) are JSON objects in stdout:

```json
{
  "source": "google_search",
  "query": "machine learning",
  "results": [
    {"title": "...", "url": "...", "snippet": "..."},
    ...
  ],
  "meta": {
    "fetched_at": "2025-01-01T00:00:00Z",
    "result_count": 10
  }
}
```

With `--stream`: each result item is printed on a separate line (NDJSON):
```
{"title": "...", "url": "...", "snippet": "..."}
{"title": "...", "url": "...", "snippet": "..."}
```

With `--fields title,url`: only requested fields are returned.

---

## Error Handling

| Exit Code | Meaning | Recommended Action |
|-----------|---------|-------------------|
| 0 | Success | Parse stdout as JSON |
| 1 | General error | Log stderr, report to user |
| 2 | Timeout | Retry with `--timeout 600`, or report server slow |
| 3 | Source not found | Run `sources list`, pick valid source |
| 4 | Server unavailable | Report infrastructure issue, do not retry in loop |
| 5 | Invalid input | Fix source name or query format |

Error details are always in **stderr**, not stdout. Stdout is reserved for clean data output.

---

## Schema Discovery

Before calling a source, inspect its schema:
```bash
ayga_parser sources info google_search
```

Output includes: description, returned fields with types, and usage examples.

---

## Helper Commands

For multi-step operations, use `+verb` helpers:
```bash
ayga_parser +extract extract <url>      # Fetch URL + convert to Markdown
ayga_parser +research research <query>  # Combine google_search + perplexity
```

**Rule:** Use a helper only when a single `get` call is insufficient. If one source call does the job, use `get` directly.

---

## Quick Examples

```bash
# Web search
ayga_parser get google_search "climate change 2025" --fields title,url,snippet

# Get full article as Markdown
ayga_parser +extract extract "https://example.com/article"

# AI answer with timeout
ayga_parser get perplexity "What is quantum entanglement?" --timeout 120

# Stream search results (NDJSON)
ayga_parser get google_search "Python tutorials" --stream --fields title,url

# Debug: see what would be sent
ayga_parser get google_search "test" --dry-run
```
