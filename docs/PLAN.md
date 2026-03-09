# Development Plan
# A-Parser CLI Tool & AYGA MCP Integration

**Date:** 2026-03-07
**Epic:** P-XXX
**Status:** Planning

## Phase 1: Core CLI Foundation (Week 1)
**Goal:** Create a robust Typer-based CLI with basic HTTP API support.

- [ ] **Task 1.1:** Scaffold project structure (Typer, pyproject.toml, pytest).
- [ ] **Task 1.2:** Implement robust `Config` class using Pydantic (loading from `~/.config/aparser/` and ENV).
- [ ] **Task 1.3:** Build `AparserHttpClient` wrapping all 17 documented API methods.
- [ ] **Task 1.4:** Implement basic CLI commands: `ping`, `info`, `parsers list`.
- [ ] **Task 1.5:** Implement `aparser http request` command for synchronous parsing.

## Phase 2: Redis Asynchronous Queue (Week 2)
**Goal:** High-throughput queuing system.

- [ ] **Task 2.1:** Implement `AparserRedisClient` using `redis.asyncio`.
- [ ] **Task 2.2:** Build `aparser redis push` command (LPUSH to `aparser_redis_api`).
- [ ] **Task 2.3:** Build `aparser redis wait` (BLPOP from `aparser_results` with timeout).
- [ ] **Task 2.4:** Build pipeline tools: `aparser bulk --file domains.txt --async`.
- [ ] **Task 2.5:** Add Rich-based progress bars for blocking waits.

## Phase 3: AYGA MCP Integration (Week 3)
**Goal:** Make A-Parser accessible to AI Agents natively.

- [ ] **Task 3.1:** Scaffold simple MCP Server using Anthropic/Ayga SDK.
- [ ] **Task 3.2:** Expose `get_parsers_list` as an MCP tool.
- [ ] **Task 3.3:** Expose `parse_query(parser_name, query)` as an MCP tool (wrapping CLI subprocess or library directly).
- [ ] **Task 3.4:** Handle timeout states gracefully in context, returning "Job Queued: ID".
- [ ] **Task 3.5:** Create `check_job_status(job_id)` tool for agents to retrieve delayed results.

## Phase 4: Zero-Trust QA & Docs (Week 4)
**Goal:** Production readiness.

- [ ] **Task 4.1:** Write Pytest unit tests for JSON payload construction.
- [ ] **Task 4.2:** E2E tests mocking Redis queue responses.
- [ ] **Task 4.3:** Publish full `README.md` and CLI `--help` examples.
- [ ] **Task 4.4:** Sync all Agent-Tools mappings into Notion for observability.
