---
name: ayga-cli
description: "Data access client — fetch data from configured sources via Redis Wrapper. Returns structured JSON. No knowledge of parsers, proxies, or infrastructure required."
version: 0.1.0
trigger: "use when you need to fetch data from the web, extract article content from URLs, get AI-generated answers, search news, or retrieve any data where the source type is known"
category: data-access
platforms: [linux, macos]
---

# ayga-cli

Fetch data from configured sources. The server (Redis Wrapper) handles all infrastructure — parsers, proxies, presets. You only specify what you want and from which source.

## When to Use
- Web search results needed
- Extracting clean text from a URL
- Getting AI-generated answers to questions
- Researching a topic from multiple angles
- Any structured data retrieval where source type is known

## Quick Start

```bash
# 1. See what sources are available on this server
ayga_parser sources list

# 2. Fetch data (use --fields to protect context window)
ayga_parser get google_search "machine learning 2025" --fields title,url,snippet

# 3. Stream results as NDJSON (one record per line)
ayga_parser get google_search "query" --stream

# 4. Get schema for a source before using it
ayga_parser sources info google_search

# 5. Multi-step helpers
ayga_parser +extract extract https://example.com/article   # URL -> Markdown
ayga_parser +research research "quantum computing"          # google_search + perplexity combined
```

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success — data in stdout | Parse stdout as JSON |
| 1 | General error | Check stderr |
| 2 | Timeout | Retry with `--timeout 600` |
| 3 | Source not found | Run `sources list` |
| 4 | Server unavailable | Infrastructure issue, do not retry in loop |
| 5 | Invalid input | Fix source name or query |

## Flags Reference

```
--fields title,url,snippet   Filter response to specific fields (dot-notation supported)
--stream                     Output NDJSON — one record per line (ideal for lists)
--dry-run                    Show what would be sent without executing
--json / -j                  Machine-readable JSON output
--timeout N                  Timeout in seconds (default: 300)
```

## Output Format

Stdout: JSON. Stderr: errors only.

```json
{"results": [{"title": "...", "url": "...", "snippet": "..."}]}
```

With `--stream`:
```
{"title": "...", "url": "...", "snippet": "..."}
{"title": "...", "url": "...", "snippet": "..."}
```

## Pitfalls

- Always run `sources list` first — available sources depend on server configuration, there is no hardcoded list
- Use `--fields` in agent contexts to avoid large payloads overwhelming context window
- Exit code `4` means Redis Wrapper is down — do NOT retry in a tight loop
- `+research` sends two parallel jobs; if one times out, partial results are returned (no crash)
- Source names are the registry `id` — lowercase with underscores, e.g. `google_search`, `perplexity`, `article_extractor`
- `--stream` and `--json` can be combined with `--fields` for efficient pipelined output
- Use `sources info <name>` before calling an unfamiliar source to understand its response schema
