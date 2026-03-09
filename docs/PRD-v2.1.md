# Product Requirements Document (PRD)
# A-Parser CLI v2.1 — Dynamic Discovery Architecture

**Version:** 2.1  
**Date:** 2026-03-07  
**Status:** Ready for Development  
**Owner:** Ozand  
**Lead Architect:** Gubin 🤖

---

## 1. Executive Summary

### 1.1 Problem Statement
Current A-Parser CLI v1.0 has critical architectural flaws:
- **Hardcoded parsers:** Only 3 parsers known, missing 100+ including `FreeAI::Perplexity`
- **Static commands:** CLI doesn't adapt to A-Parser instance capabilities
- **No discovery:** Agents must know parser names in advance
- **No caching:** Every call fetches fresh data from API
- **Single-phase parsing:** Can't validate parser-specific arguments

### 1.2 Solution
**Dynamic Discovery Architecture** — CLI that:
1. Discovers all available parsers at runtime via `getParsersList` + `getParserInfo`
2. Caches manifest locally (24h TTL)
3. Builds commands dynamically based on actual A-Parser capabilities
4. Validates arguments using parser schemas (two-phase parsing)
5. Supports fuzzy search for parser discovery

### 1.3 Success Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| Parser discovery | 100% | All parsers from `getParsersList` available |
| Cache hit rate | >90% | Local manifest usage vs API calls |
| Fuzzy search accuracy | >85% | Find correct parser by keywords |
| Argument validation | 100% | Zero invalid API calls due to typos |
| Dry-run coverage | 100% | All commands support `--dry-run` |

---

## 2. User Stories

### 2.1 Agent Discovery (Primary)
**As an** AI agent  
**I want** to find available parsers without knowing their exact names  
**So that** I can use `FreeAI::Perplexity` even if I only remember "AI search"

**Acceptance Criteria:**
- [ ] `search_parsers("perplexity")` returns `FreeAI::Perplexity`
- [ ] `search_parsers("AI")` returns all AI-related parsers
- [ ] Results include description and keywords for each parser

### 2.2 Dynamic Command Building
**As a** CLI user  
**I want** commands to adapt to my A-Parser instance  
**So that** I see only available parsers and their actual parameters

**Acceptance Criteria:**
- [ ] `aparser run <parser>` shows parser-specific flags dynamically
- [ ] Unknown parsers produce helpful "Did you mean...?" suggestions
- [ ] Parser parameters validated before API call

### 2.3 Safe Execution
**As an** automation engineer  
**I want** to preview what will happen before execution  
**So that** I don't waste resources on wrong queries

**Acceptance Criteria:**
- [ ] `--dry-run` shows exact API payload without sending
- [ ] `--page-all` handles pagination automatically
- [ ] Invalid arguments caught locally, not by API

### 2.4 Performance
**As a** frequent user  
**I want** fast command completion  
**So that** I don't wait for API on every tab-completion

**Acceptance Criteria:**
- [ ] First run: <5s to build manifest cache
- [ ] Subsequent runs: <100ms to load from cache
- [ ] Cache auto-refreshes every 24h
- [ ] Manual refresh: `aparser parsers sync`

---

## 3. Functional Requirements

### 3.1 Manifest Management

#### FR-001: Manifest Sync
```
Command: aparser parsers sync [--force]
Behavior:
  1. Call getParsersList API
  2. For each parser: call getParserInfo
  3. Build complete manifest with:
     - parser name
     - description
     - category
     - available presets
     - parameter schemas
     - keywords (for fuzzy search)
  4. Save to ~/.config/aparser-cli/manifest.json
  5. Set TTL: 24 hours
```

#### FR-002: Cache Validation
```
On every CLI start:
  1. Check if manifest.json exists
  2. Check if TTL expired (<24h old)
  3. If expired or missing: auto-sync (async, non-blocking)
  4. Use cached manifest for immediate commands
```

#### FR-003: Fuzzy Search Index
```
Build inverted index from manifest:
  {
    "perplexity": ["FreeAI::Perplexity"],
    "ai": ["FreeAI::Perplexity", "FreeAI::ChatGPT", ...],
    "google": ["SE::Google", "SE::GoogleNews", ...],
    "search": ["SE::Google", "SE::Yandex", "FreeAI::Perplexity", ...]
  }
Search algorithm: fuzzy matching with Levenshtein distance
```

### 3.2 Dynamic CLI Commands

#### FR-004: Two-Phase Command Parser
```
Phase 1: Identify parser
  Input: aparser run FreeAI::Perplexity --depth 5 "query"
  Action: Load parser schema from manifest
  Output: Known parser with validated parameters

Phase 2: Validate and execute
  Validate: --depth is int, within allowed range
  Transform: Build API payload
  Execute: Send to A-Parser via Redis/HTTP
```

#### FR-005: Dynamic Help Generation
```
aparser run FreeAI::Perplexity --help

Output (generated from manifest):
  Usage: aparser run FreeAI::Perplexity [OPTIONS] QUERY
  
  AI-powered search via Perplexity
  
  Options:
    --depth INTEGER     Depth of related questions (1-10) [default: 3]
    --sources TEXT      Comma-separated source filters
    --preset TEXT       Preset name [default: default]
    --dry-run          Show what would be executed
    --page-all         Auto-pagination
```

### 3.3 MCP Server Enhancements

#### FR-006: Enhanced search_parsers
```python
@mcp.tool()
async def search_parsers(
    query: str,
    category: Optional[str] = None,
    limit: int = 10
) -> List[ParserInfo]:
    """
    Fuzzy search through all available parsers.
    
    Examples:
      "perplexity" → FreeAI::Perplexity
      "AI search" → [FreeAI::Perplexity, FreeAI::ChatGPT, ...]
      "google" → [SE::Google, SE::GoogleNews, ...]
    """
```

#### FR-007: get_parser_schema
```python
@mcp.tool()
async def get_parser_schema(parser: str) -> Dict:
    """
    Get complete schema for parser including all parameters.
    
    Returns:
      {
        "name": "FreeAI::Perplexity",
        "description": "AI-powered search",
        "parameters": {
          "depth": {"type": "integer", "min": 1, "max": 10, "default": 3},
          "sources": {"type": "string", "optional": true}
        },
        "presets": ["default", "academic", "fast"]
      }
    """
```

#### FR-008: validate_parser_call
```python
@mcp.tool()
async def validate_parser_call(
    parser: str,
    query: str,
    options: Dict
) -> ValidationResult:
    """
    Validate parameters before execution.
    Returns errors if any, or success with transformed payload.
    """
```

### 3.4 Utility Features

#### FR-009: --dry-run Flag
```
For any command:
  aparser run SE::Google "test" --dry-run
  
Output:
  [DRY RUN] Would execute:
    Parser: SE::Google
    Query: "test"
    Preset: default
    Options: {pagecount: 1}
    Redis queue: aparser_redis_api
    Expected result queue: aparser_result_abc123
```

#### FR-010: --page-all Flag
```
aparser run SE::Google "test" --page-all --max-pages 10

Behavior:
  1. Execute page 1
  2. If results truncated, auto-queue pages 2-N
  3. Collect all results
  4. Return combined output
```

---

## 4. Non-Functional Requirements

### 4.1 Performance
- **NFR-001:** Manifest sync <5s for 100+ parsers
- **NFR-002:** Cache load <100ms
- **NFR-003:** Fuzzy search <50ms for 1000+ entries
- **NFR-004:** Command completion <200ms

### 4.2 Reliability
- **NFR-005:** Graceful degradation if A-Parser API unavailable (use stale cache)
- **NFR-006:** Automatic retry on sync failure (3 attempts)
- **NFR-007:** Cache corruption detection and auto-rebuild

### 4.3 Security
- **NFR-008:** Manifest stored with same permissions as config (600)
- **NFR-009:** No sensitive data in manifest (only public parser metadata)

---

## 5. Architecture Overview

### 5.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        USER                                  │
│  (Human / AI Agent / Cron)                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────▼───────────┐
           │   A-Parser CLI v2.1   │
           │  ┌─────────────────┐  │
           │  │  Command Router │  │
           │  │  (Two-Phase)    │  │
           │  └────────┬────────┘  │
           │           │           │
           │  ┌────────▼────────┐  │
           │  │ Manifest Cache  │  │
           │  │  (24h TTL)      │  │
           │  └────────┬────────┘  │
           │           │           │
           │  ┌────────▼────────┐  │
           │  │ Fuzzy Search    │  │
           │  │ Engine          │  │
           │  └────────┬────────┘  │
           │           │           │
           │  ┌────────▼────────┐  │
           │  │ Schema Validator│  │
           │  └─────────────────┘  │
           └───────────┬───────────┘
                       │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼───────┐ ┌────▼──────────┐
│   Manifest   │ │   A-Parser   │ │   Redis       │
│   Cache File │ │   HTTP API   │ │   Queue       │
│   (JSON)     │ │   (getInfo)  │ │   (jobs)      │
└──────────────┘ └──────────────┘ └───────────────┘
```

### 5.2 Data Flow

```
1. User: aparser run FreeAI::Perplexity --depth 5 "query"
   │
2. CLI: Load manifest from cache
   │
3. CLI: Fuzzy match "FreeAI::Perplexity" → confirm exact name
   │
4. CLI: Load schema for FreeAI::Perplexity
   │
5. CLI: Validate --depth 5 (int, 1-10) ✓
   │
6. CLI: Build API payload
   │
7. [if --dry-run] Show payload, exit
   │
8. CLI: Submit to Redis queue
   │
9. CLI: Return job_id for tracking
```

---

## 6. Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Manifest sync command (`aparser parsers sync`)
- [ ] Cache storage and TTL management
- [ ] Basic fuzzy search index

### Phase 2: Dynamic Commands (Week 2)
- [ ] Two-phase command parser
- [ ] Dynamic help generation
- [ ] Schema validation

### Phase 3: MCP Enhancement (Week 3)
- [ ] Enhanced `search_parsers` with fuzzy matching
- [ ] `get_parser_schema` tool
- [ ] `validate_parser_call` tool

### Phase 4: Utilities (Week 4)
- [ ] `--dry-run` implementation
- [ ] `--page-all` implementation
- [ ] Performance optimization

---

## 7. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| A-Parser API breaking changes | Low | High | Version pinning, abstraction layer |
| Large manifest size (>10MB) | Medium | Medium | Compression, lazy loading |
| Fuzzy search false positives | Medium | Low | Confidence threshold, explicit confirmation |
| Cache stale data | Medium | Medium | TTL + manual sync + stale warning |

---

## 8. Appendix

### 8.1 Related Documents
- Architecture: `ARCHITECTURE-v2.1.md`
- Backlog: `BACKLOG-v2.1.md`
- Research: `research/repo-analysis-report.md`

### 8.2 Reference Implementations
- Google Workspace CLI: dynamic command surface
- CLIHub: passthrough JSON pattern
- Anthropic PTC: programmatic tool calling

---

**Approved by:** [Pending Ozand confirmation]  
**Next Step:** Create detailed backlog and launch subagent development
