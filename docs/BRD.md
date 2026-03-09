# Business Requirements Document (BRD)
# A-Parser CLI Tool & AYGA MCP Integration

**Version:** 1.0  
**Date:** 2026-03-07  
**Status:** In Development  
**Epic:** P-XXX (A-Parser CLI)  

---

## 1. Executive Summary

### 1.1 Problem Statement
Current A-Parser integration requires manual HTTP API calls or PHP clients. No modern CLI tool exists for:
- Queue-based asynchronous parsing (Redis)
- Integration with AI agent pipelines (AYGA MCP)
- Automated, scriptable parsing workflows

### 1.2 Solution
A-Parser CLI (GTV) — hybrid Python CLI supporting both Redis (production) and HTTP (fallback) modes, with native AYGA MCP integration.

### 1.3 Success Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| CLI latency | <100ms | Queue operation time |
| Throughput | 1000+ req/sec | Redis LPUSH benchmark |
| API coverage | 100% | All 17 HTTP methods + Redis patterns |
| Test coverage | >80% | pytest coverage report |
| Manual testing | 0% | Zero-Trust QA automated |

---

## 2. Business Objectives

### 2.1 Primary Objectives
1. **Enable AI Agent Integration** — AYGA MCP can delegate parsing without blocking
2. **Reduce Token Waste** — No repeated HTTP calls in main session
3. **Foundation for Pipelines** — Multi-parser, distributed processing support

### 2.2 Secondary Objectives
1. **Developer Experience** — Modern CLI with auto-completion, rich output
2. **Operational Visibility** — Metrics, monitoring, alerting
3. **Extensibility** — Plugin architecture for custom parsers

---

## 3. Stakeholders

| Role | Name | Needs |
|------|------|-------|
| Primary User | Gubin/k7000 (AI agents) | Programmatic access, async operations |
| Secondary User | Ozand (manual ops) | Debugging, one-off queries |
| System | AYGA MCP | Redis queue integration |
| Future | External developers | Documentation, examples |

---

## 4. Functional Requirements

### 4.1 Core Features

#### FR-001: Redis Queue Operations
- **Description:** Submit parsing jobs via Redis LPUSH
- **Priority:** P0
- **Acceptance Criteria:**
  - [ ] `aparser redis push <parser> <query>` submits job
  - [ ] Returns unique queryId immediately
  - [ ] Supports batch file input (`--file`)
  - [ ] Configurable output queue (`--output-queue`)

#### FR-002: Result Retrieval
- **Description:** Retrieve results via Redis BLPOP
- **Priority:** P0
- **Acceptance Criteria:**
  - [ ] `aparser redis pop <queue>` retrieves result
  - [ ] Blocking wait with timeout (`--wait`, `--timeout`)
  - [ ] Auto-parse JSON results
  - [ ] Support multiple output formats (table, json, csv)

#### FR-003: HTTP Fallback
- **Description:** Direct HTTP API when Redis unavailable
- **Priority:** P1
- **Acceptance Criteria:**
  - [ ] `aparser http request <parser> <query>`
  - [ ] All 17 HTTP methods supported
  - [ ] Automatic fallback from Redis mode
  - [ ] Same output format as Redis mode

#### FR-004: Task Management
- **Description:** Monitor and manage parsing tasks
- **Priority:** P1
- **Acceptance Criteria:**
  - [ ] `aparser task status <queryId>`
  - [ ] `aparser task list` (active/completed)
  - [ ] `aparser task cancel <queryId>`
  - [ ] Queue depth metrics

#### FR-005: Pipeline Mode
- **Description:** Producer-consumer for batch processing
- **Priority:** P2
- **Acceptance Criteria:**
  - [ ] `aparser pipeline produce --input-file`
  - [ ] `aparser pipeline consume --output-queue`
  - [ ] Parallel processing support
  - [ ] Progress bars and ETA

### 4.2 Integration Requirements

#### IR-001: AYGA MCP
- **Description:** Native MCP tool integration
- **Priority:** P0
- **Acceptance Criteria:**
  - [ ] `@mcp.tool()` decorator support
  - [ ] Async/await interface
  - [ ] Error handling and retries
  - [ ] Result caching

#### IR-002: Cron Jobs
- **Description:** Systemd cron compatibility
- **Priority:** P1
- **Acceptance Criteria:**
  - [ ] Non-interactive mode (`--json` output)
  - [ ] Exit codes for success/failure
  - [ ] Log rotation support
  - [ ] Environment variable configuration

---

## 5. Non-Functional Requirements

### 5.1 Performance
- **NFR-001:** CLI startup <100ms
- **NFR-002:** Redis operation <5ms (local)
- **NFR-003:** HTTP operation <500ms (local A-Parser)
- **NFR-004:** Memory usage <50MB resident

### 5.2 Reliability
- **NFR-005:** 99.9% uptime (Redis mode)
- **NFR-006:** Automatic retry with exponential backoff
- **NFR-007:** Graceful degradation to HTTP mode
- **NFR-008:** Connection pooling (HTTP)

### 5.3 Security
- **NFR-009:** No hardcoded credentials
- **NFR-010:** Environment variable or config file for secrets
- **NFR-011:** Password masking in logs
- **NFR-012:** Input validation and sanitization

### 5.4 Usability
- **NFR-013:** Rich help text with examples
- **NFR-014:** Shell auto-completion (bash, zsh, fish)
- **NFR-015:** Progress indicators for long operations
- **NFR-016:** Color-coded output (success/error/warning)

---

## 6. Technical Constraints

### 6.1 Technology Stack
- **Language:** Python 3.10+
- **CLI Framework:** Typer
- **HTTP Client:** httpx
- **Redis Client:** redis-py + aioredis
- **Config:** Pydantic Settings
- **Output:** Rich
- **Testing:** pytest + pytest-asyncio

### 6.2 Dependencies
- A-Parser instance (local or remote)
- Redis server (optional, for production)
- Python 3.10+

### 6.3 Compatibility
- **OS:** Linux (primary), macOS (secondary), Windows (best effort)
- **A-Parser:** v2.x API
- **Redis:** v6.0+

---

## 7. Project Timeline

### Phase 1: MVP (4 weeks)
- Week 1: Project setup, HTTP client, basic commands
- Week 2: Redis client, queue operations
- Week 3: AYGA MCP integration, testing
- Week 4: Documentation, examples, release

### Phase 2: Enhanced (2 weeks)
- Pipeline mode
- Multi-parser support
- Advanced monitoring

### Phase 3: Ecosystem (ongoing)
- Community parsers
- Plugin architecture
- Cloud deployment

---

## 8. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Redis not available | Low | Medium | HTTP fallback mode |
| Queue overflow | Medium | High | Monitor depth, alert >10K |
| Result TTL expired | Low | Medium | Warn if not fetched within TTL/2 |
| Parser crash mid-job | Low | High | Queue preserves requests, retry |
| A-Parser API changes | Low | High | Version pinning, abstraction layer |

---

## 9. Glossary

- **AYGA MCP** — Model Context Protocol for AYGA AI agents
- **BLPOP** — Redis blocking list pop operation
- **GTV** — Gateway to External Data (project codename)
- **LPUSH** — Redis list push operation
- **MCP** — Model Context Protocol (Anthropic standard)
- **TTL** — Time To Live (Redis key expiration)

---

## 10. Appendices

### Appendix A: A-Parser API Methods
See: `docs/a-parser-api-reference.md`

### Appendix B: Redis Queue Patterns
See: `docs/redis-queue-patterns.md`

### Appendix C: Council of Directors Session
See: `docs/councils/aparser-cli-session-1.md`

---

**Document Owner:** Gubin 🤖  
**Reviewers:** Ozand  
**Approval Date:** TBD
