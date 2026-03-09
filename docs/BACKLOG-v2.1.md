# Development Backlog
# A-Parser CLI v2.1 — Dynamic Discovery

**Sprint:** v2.1  
**Duration:** 4 weeks  
**Team:** GPT-5.3 Codex Subagents (parallel development)

---

## Sprint Backlog

### Week 1: Foundation — Manifest & Cache

#### Task 1.1: Manifest Sync Command
**Assignee:** Subagent-1 (Foundation)  
**Priority:** P0  
**Estimate:** 2 days

**Description:**
Implement `aparser parsers sync` command that fetches complete parser catalog from A-Parser API.

**Acceptance Criteria:**
- [ ] Call `getParsersList` API method
- [ ] For each parser: call `getParserInfo` 
- [ ] Build comprehensive manifest with:
  - parser name, description, category
  - available presets and their configs
  - parameter schemas (name, type, min/max, default)
  - keywords for fuzzy search
- [ ] Save to `~/.config/aparser-cli/manifest.json`
- [ ] Implement 24h TTL mechanism
- [ ] Add `--force` flag to bypass TTL
- [ ] Progress indicator for long sync

**API Methods:**
```python
# getParsersList
{"password": "...", "action": "getParsersList"}
# Returns: {"success": 1, "data": ["SE::Google", "FreeAI::Perplexity", ...]}

# getParserInfo
{"password": "...", "action": "getParserInfo", "data": {"parser": "FreeAI::Perplexity"}}
# Returns: {"success": 1, "data": {"name": "...", "description": "...", "options": [...]}}
```

**Files:**
- `src/aparser_cli/commands/parsers.py` — add `sync` subcommand
- `src/aparser_cli/manifest.py` — new module for manifest operations

---

#### Task 1.2: Cache Management
**Assignee:** Subagent-1 (Foundation)  
**Priority:** P0  
**Estimate:** 2 days

**Description:**
Implement cache storage with TTL, auto-refresh, and corruption handling.

**Acceptance Criteria:**
- [ ] Cache file location: `~/.config/aparser-cli/manifest.json`
- [ ] File permissions: 600 (owner read/write only)
- [ ] TTL check on every CLI start
- [ ] Auto-refresh in background if expired
- [ ] Graceful use of stale cache if API unavailable
- [ ] Cache corruption detection (JSON validation)
- [ ] Auto-rebuild on corruption
- [ ] Cache metadata: created_at, version, parser_count

**Implementation:**
```python
class ManifestCache:
    def load(self) -> Manifest
    def save(self, manifest: Manifest)
    def is_expired(self) -> bool
    def is_corrupted(self) -> bool
    def get_age_hours(self) -> float
```

---

#### Task 1.3: Fuzzy Search Index
**Assignee:** Subagent-1 (Foundation)  
**Priority:** P0  
**Estimate:** 2 days

**Description:**
Build inverted index for fuzzy parser search.

**Acceptance Criteria:**
- [ ] Extract keywords from parser names and descriptions
- [ ] Build inverted index: `{keyword: [parser_names]}`
- [ ] Levenshtein distance for typo tolerance
- [ ] Ranking by relevance (exact match > partial > fuzzy)
- [ ] Search "perplexity" → finds "FreeAI::Perplexity"
- [ ] Search "AI" → finds all AI-related parsers
- [ ] Search "google" → finds SE::Google, SE::GoogleNews, etc.
- [ ] Max 10 results, sorted by relevance

**Algorithm:**
```python
def search_parsers(query: str, limit: int = 10) -> List[ParserMatch]:
    # 1. Exact match
    # 2. Prefix match
    # 3. Substring match
    # 4. Fuzzy match (Levenshtein <= 2)
    # 5. Keyword match from inverted index
    # Return ranked results
```

---

### Week 2: Dynamic Commands

#### Task 2.1: Two-Phase Command Parser
**Assignee:** Subagent-2 (Commands)  
**Priority:** P0  
**Estimate:** 3 days

**Description:**
Implement two-phase parsing: first identify parser, then validate arguments using its schema.

**Acceptance Criteria:**
- [ ] Phase 1: Parse command line, identify parser name
- [ ] Phase 2: Load parser schema from manifest
- [ ] Phase 3: Re-parse with parser-specific arguments
- [ ] Phase 4: Validate all arguments against schema
- [ ] Support for: strings, integers, floats, booleans, enums
- [ ] Range validation (min/max for numbers)
- [ ] Enum validation (allowed values)
- [ ] Required vs optional parameters
- [ ] Type coercion (string "5" → int 5)

**Example:**
```bash
# Input
aparser run FreeAI::Perplexity --depth 5 "query"

# Phase 1: parser = "FreeAI::Perplexity"
# Phase 2: schema = {depth: {type: int, min: 1, max: 10}}
# Phase 3: args = {depth: 5, query: "query"}
# Phase 4: validate 5 is int and 1 <= 5 <= 10 ✓
```

---

#### Task 2.2: Dynamic Help Generation
**Assignee:** Subagent-2 (Commands)  
**Priority:** P0  
**Estimate:** 2 days

**Description:**
Generate help text dynamically from parser schema.

**Acceptance Criteria:**
- [ ] `aparser run <parser> --help` shows parser-specific help
- [ ] Description from manifest
- [ ] All parameters with types and defaults
- [ ] Required parameters marked
- [ ] Examples section
- [ ] Related parsers section

**Output Example:**
```
Usage: aparser run FreeAI::Perplexity [OPTIONS] QUERY

AI-powered search via Perplexity. Returns structured answers with sources.

Arguments:
  QUERY  Search query [required]

Options:
  --depth INTEGER     Number of related questions to explore [1-10] [default: 3]
  --sources TEXT      Filter sources (comma-separated) [optional]
  --preset TEXT       Configuration preset [default: default]
  
  --dry-run          Show what would be executed without running
  --page-all         Automatically fetch all result pages
  
Examples:
  aparser run FreeAI::Perplexity "What is machine learning?"
  aparser run FreeAI::Perplexity --depth 5 "Latest AI trends"

Related parsers:
  - SE::Google (traditional search)
  - FreeAI::ChatGPT (conversational AI)
```

---

#### Task 2.3: Smart Suggestions
**Assignee:** Subagent-2 (Commands)  
**Priority:** P1  
**Estimate:** 2 days

**Description:**
When parser not found, suggest closest matches.

**Acceptance Criteria:**
- [ ] Unknown parser: "Did you mean...?" with top 3 fuzzy matches
- [ ] Typo tolerance: "perplexyty" → "FreeAI::Perplexity"
- [ ] Category suggestions: "AI parser" → list all AI parsers
- [ ] Integration with fuzzy search index

---

### Week 3: MCP Server Enhancement

#### Task 3.1: Enhanced search_parsers
**Assignee:** Subagent-3 (MCP)  
**Priority:** P0  
**Estimate:** 2 days

**Description:**
Rewrite `search_parsers` MCP tool with fuzzy matching and rich results.

**Acceptance Criteria:**
- [ ] Fuzzy search using manifest index
- [ ] Return rich metadata: name, description, category, keywords
- [ ] Support category filter
- [ ] Configurable limit (default 10)
- [ ] Confidence score for each result
- [ ] Example queries in response

**Tool Schema:**
```python
@mcp.tool()
async def search_parsers(
    query: str,
    category: Optional[str] = None,
    limit: int = 10,
    min_confidence: float = 0.5
) -> List[ParserMatch]:
    """
    Search available parsers using fuzzy matching.
    
    Args:
        query: Search query (name, keyword, or description)
        category: Filter by category (e.g., "SE", "FreeAI", "Net")
        limit: Maximum results (1-50)
        min_confidence: Minimum match confidence (0.0-1.0)
    
    Returns:
        List of matching parsers with confidence scores
    """
```

---

#### Task 3.2: get_parser_schema Tool
**Assignee:** Subagent-3 (MCP)  
**Priority:** P0  
**Estimate:** 2 days

**Description:**
New MCP tool to get complete parser schema for validation.

**Acceptance Criteria:**
- [ ] Return complete schema for any parser
- [ ] Include all parameters with types, ranges, defaults
- [ ] Include available presets
- [ ] Include example valid calls
- [ ] Error if parser not found

**Tool Schema:**
```python
@mcp.tool()
async def get_parser_schema(parser: str) -> ParserSchema:
    """
    Get complete schema for a parser.
    
    Args:
        parser: Exact parser name (e.g., "FreeAI::Perplexity")
    
    Returns:
        {
            "name": "FreeAI::Perplexity",
            "description": "AI-powered search",
            "category": "FreeAI",
            "parameters": {
                "depth": {
                    "type": "integer",
                    "description": "Number of related questions",
                    "min": 1,
                    "max": 10,
                    "default": 3,
                    "required": false
                }
            },
            "presets": ["default", "academic", "fast"],
            "example_queries": ["What is AI?", "Latest news"]
        }
    """
```

---

#### Task 3.3: validate_parser_call Tool
**Assignee:** Subagent-3 (MCP)  
**Priority:** P1  
**Estimate:** 2 days

**Description:**
Validate parameters before execution to catch errors early.

**Acceptance Criteria:**
- [ ] Validate all parameters against schema
- [ ] Return detailed error messages
- [ ] Suggest corrections for common mistakes
- [ ] Show transformed payload
- [ ] Dry-run mode support

---

### Week 4: Utilities & Polish

#### Task 4.1: --dry-run Implementation
**Assignee:** Subagent-4 (Utilities)  
**Priority:** P0  
**Estimate:** 2 days

**Description:**
Preview mode for all commands.

**Acceptance Criteria:**
- [ ] `--dry-run` flag for all run commands
- [ ] Show exact API payload
- [ ] Show expected result queue name
- [ ] Estimate execution time
- [ ] Show resource usage (threads, memory)
- [ ] Exit code 0 (success) even in dry-run

**Output Example:**
```
[DRY RUN] Execution plan:
  Parser: FreeAI::Perplexity
  Query: "What is machine learning?"
  Parameters:
    depth: 3
    sources: null
  Preset: default
  
  Transport: Redis (aparser_redis_api)
  Expected result queue: aparser_result_abc123
  Estimated time: 5-10 seconds
  
  API Payload:
    {"password": "***", "action": "oneRequest", "data": {...}}
```

---

#### Task 4.2: --page-all Implementation
**Assignee:** Subagent-4 (Utilities)  
**Priority:** P0  
**Estimate:** 2 days

**Description:**
Automatic pagination handling.

**Acceptance Criteria:**
- [ ] Detect truncated results in response
- [ ] Auto-queue subsequent pages
- [ ] Collect all results
- [ ] Combine into single output
- [ ] `--max-pages` limit (default 10)
- [ ] Progress indicator
- [ ] Handle partial failures gracefully

---

#### Task 4.3: Performance Optimization
**Assignee:** Subagent-4 (Utilities)  
**Priority:** P1  
**Estimate:** 2 days

**Description:**
Optimize for speed and resource usage.

**Acceptance Criteria:**
- [ ] Lazy loading of manifest (load on first use)
- [ ] Compression for cache file (gzip)
- [ ] Memory-efficient fuzzy search (Bloom filter)
- [ ] Parallel manifest sync (async)
- [ ] Benchmark: <100ms for cached operations
- [ ] Profile and optimize hot paths

---

## Subagent Assignment

| Subagent | Focus Area | Tasks | Model |
|----------|-----------|-------|-------|
| **Subagent-1** | Foundation | 1.1, 1.2, 1.3 | GPT-5.3 Codex |
| **Subagent-2** | Commands | 2.1, 2.2, 2.3 | GPT-5.3 Codex |
| **Subagent-3** | MCP Server | 3.1, 3.2, 3.3 | GPT-5.3 Codex |
| **Subagent-4** | Utilities | 4.1, 4.2, 4.3 | GPT-5.3 Codex |

## Parallel Development Strategy

```
Week 1: Subagent-1 (Foundation)
        ↓
Week 2: Subagent-2 (Commands) uses Foundation
        ↓
Week 3: Subagent-3 (MCP) uses Commands
        ↓
Week 4: Subagent-4 (Utilities) integrates all
```

Some parallel work possible after Week 1 Foundation complete.

## Definition of Done

- [ ] All 12 tasks completed
- [ ] 107 existing tests pass
- [ ] New tests: >80% coverage for new code
- [ ] Documentation updated
- [ ] Performance benchmarks met
- [ ] Ozand approval

---

**Ready for subagent launch:** [Pending Ozand confirmation]
