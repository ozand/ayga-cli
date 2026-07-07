# Repository Analysis Report: CLI vs MCP Architecture

## 1. Executive Summary
This report analyzes core architectural patterns for the ayga-parser CLI based on Google Workspace CLI, CLIHub, MCP CLI, Anthropic practices, and recent architectural articles. 

**Key conclusion:** Traditional MCP implementations are powerful but context-heavy ("Instruction Manual Tax"). The most successful modern agentic tools focus on dynamic discovery, structured JSON-first output, and "Lazy Loading" of tool definitions to save tokens and improve agent accuracy.

## 2. Repository-by-Repository Analysis

### 2.1 Google Workspace CLI (`googleworkspace/cli`)
* **Pattern: Dynamic Command Surface.** Unlike static CLIs, it reads the Google Discovery Service at runtime to build its command tree. This ensures it's always up-to-date with API changes without requiring a new CLI release.
* **Pattern: Two-Phase Parsing.** It identifies the service first, fetches the discovery doc (cached for 24h), builds a command tree, and then re-parses remaining arguments.
* **Security & Auth:** Supports multiple flows: Interactive OAuth, Service Accounts. Critically, it uses the **OS Keyring** with AES-256-GCM encryption for stored credentials.
* **UX Practices:** Includes `--dry-run` to preview requests and `--page-all` for automatic pagination handling—essential for complex API scrapers.

### 2.2 CLI Hub (`thellimist/clihub`)
* **Philosophy:** "Turn any MCP server into a compiled CLI binary." 
* **Pattern: Codegen.** It doesn't just wrap MCP; it *generates* a CLI with subcommands mapped from MCP `tools/list`.
* **UX Practice: Passthrough Mode.** Includes a `--from-json` flag for every tool, allowing agents to skip flag-parsing logic and just send the payload directly.
* **Architecture:** Compiles into a static binary with zero runtime dependencies.

### 2.3 MCP CLI (`wong2/mcp-cli`)
* **Insight:** Provides an interactive inspector and standard implementation of the MCP protocol, showing how standard clients expect tools to be presented (JSON Schema mapping).

### 2.4 Anthropic Advanced Tool Use
* **Deep Insight: Programmatic Tool Calling (PTC).** Anthropic suggests moving orchestration logic (loops, filtering, pagination) into a code execution sandbox environment rather than relying on natural language round-trips for every API call. This saves 30-50% on tokens.
* **Insight: Tool Search.** "On-demand" tool discovery keeps the agent's context window clean, only loading specific schemas when requested.

### 2.5 CLI vs MCP Article (`kanyilmaz.me`)
* **The "Instruction Manual Tax":** MCP's default behavior of dumping ALL JSON schemas into the context window at the start of a session is extremely token-expensive. 
* **Comparison:** CLI discovery via `--help` uses ~900 tokens vs MCP's ~15k for the exact same catalog of tools.

## 3. Common Patterns & Best Practices
1. **JSON-First Output:** All success and error states must be structured JSON. For long-running scraping tasks, **NDJSON (Newline Delimited JSON)** is essential for streaming results.
2. **Passthrough Flags:** Implementing a `--from-json` flag.
3. **OS Keyring:** Avoid plaintext config files for API keys.

## 4. Anti-Patterns to Avoid
* ❌ **Pre-loading all schemas:** Dumping every ayga-parser preset/tool schema into the MCP context at startup (causes Context Overflow).
* ❌ **Natural Language Pagination:** Forcing the LLM agent to explicitly call `page=1, page=2`. The CLI should handle `--page-all` under the hood.
* ❌ **Plaintext secrets:** Storing ayga-parser API passwords in `.env` or `config.json` without option for secure keyring.

## 5. Recommendations for ayga-parser CLI
1. **Hybrid Architecture:** Implement an **MCP-compatible interface** within the CLI to allow it to be used as a backend for Claude/Copilot, while maintaining standalone CLI efficiency.
2. **Dynamic Discovery:** Build the ayga-parser CLI commands dynamically based on the available parsers/presets on the specific backend instance.
3. **Lazy Loading:** Keep the agent's context window clean. Only load specific parser schemas when requested via a `search` or `help` command.

## 6. Actionable Insights for Implementation
* Update `ARCHITECTURE.md` to include a `--from-json` flag for all ayga-parser requests.
* Rethink the AYGA MCP integration: instead of exposing 100+ ayga-parser modules as 100+ MCP tools, expose **one tool** (`ayga-cli`) that allows the agent to run `--help` or `--query` dynamically.
* Implement NDJSON output support for streaming large parsing results back to the agent.
