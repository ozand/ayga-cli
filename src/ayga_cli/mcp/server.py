"""Enhanced MCP server for ayga_parser CLI integration.

Provides 4 powerful tools for AI agent integration:
1. search_parsers - Fuzzy search through all available parsers (PRIMARY discovery tool)
2. get_parser_schema - Get complete schema for a parser (ESSENTIAL before run_parser)
3. validate_parser_call - Validate parameters before execution (catches errors early)
4. run_parser - Execute parsing jobs (async via Redis or sync via HTTP)

WORKFLOW FOR AGENTS:
1. DISCOVER: Call search_parsers("your keywords") to find right parser
2. UNDERSTAND: Call get_parser_schema("FoundParser") to see parameters
3. VALIDATE: Call validate_parser_call(...) to check your parameters
4. EXECUTE: Call run_parser(...) to run the job

NEVER guess parser names. Always use search_parsers first.
"""

from typing import Any, Optional

from mcp.server import Server
from mcp.types import TextContent, Tool

from ayga_cli.client.http import AygaParserHttpClient
from ayga_cli.client.redis import AygaParserRedisClient
from ayga_cli.config import AygaParserConfig
from ayga_cli.manifest import (
    ManifestCache,
    FuzzySearchIndex,
    Manifest,
    search_parsers,
)
from ayga_cli.proxy_strategy import merge_with_proxy

# Initialize MCP server with enhanced instructions
mcp = Server(
    "ayga_parser-mcp-v2",
    instructions="""
Universal data collection tool with 150+ parsers (Search, AI, Social, WHOIS).

WORKFLOW FOR AGENTS:
1. DISCOVER: Call search_parsers("your keywords") to find right parser
2. UNDERSTAND: Call get_parser_schema("FoundParser") to see parameters
3. VALIDATE: Call validate_parser_call(...) to check your parameters
4. EXECUTE: Call run_parser(...) to run the job

NEVER guess parser names. Always use search_parsers first.

Examples:
- "perplexity" → FreeAI::Perplexity
- "AI search" → [FreeAI::Perplexity, FreeAI::ChatGPT, ...]
- "google" → [SE::Google, SE::GoogleNews, ...]
- "whois" → Net::Whois
"""
)


@mcp.list_tools()
async def list_tools() -> list[Tool]:
    """List available ayga_parser MCP tools."""
    return [
        Tool(
            name="search_parsers",
            description="""
Fuzzy search through all available parsers. This is the PRIMARY discovery tool for agents.
Use it to find parsers by keywords, not exact names.

Examples:
- "perplexity" → FreeAI::Perplexity
- "AI search" → [FreeAI::Perplexity, FreeAI::ChatGPT, ...]
- "google" → [SE::Google, SE::GoogleNews, ...]
- "whois" → Net::Whois

Args:
- query: Search keywords (fuzzy matching supported)
- category: Filter by category (SE, FreeAI, Net, SN, etc.)
- limit: Max results (1-50)
- min_confidence: Minimum match quality (0.0-1.0)

Returns: List of matching parsers with confidence scores and descriptions.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keywords (fuzzy matching supported)",
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category (e.g., 'SE', 'FreeAI', 'Net', 'SN')",
                        "default": None,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (1-50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                    "min_confidence": {
                        "type": "number",
                        "description": "Minimum match confidence (0.0-1.0)",
                        "default": 0.5,
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
            },
        ),
        Tool(
            name="get_parser_schema",
            description="""
Get complete schema for a parser. ESSENTIAL before using run_parser.
Always call this before run_parser to understand:
- What parameters are available
- What types and ranges they have
- What presets exist

Args:
- parser: Exact parser name (e.g., "FreeAI::Perplexity")

Returns: Complete schema including parameters, types, defaults, presets, and examples.
""",
            inputSchema={
                "type": "object",
                "required": ["parser"],
                "properties": {
                    "parser": {
                        "type": "string",
                        "description": "Exact parser name (e.g., 'FreeAI::Perplexity', 'SE::Google')",
                    },
                },
            },
        ),
        Tool(
            name="validate_parser_call",
            description="""
Validate parameters before execution. Catches errors early.
Use this to check your parameters before calling run_parser.
Returns detailed error messages if something is wrong.

Args:
- parser: Parser name
- query: Search query
- options: Parameter values to validate

Returns: Validation result with errors, warnings, and transformed payload ready for API.
""",
            inputSchema={
                "type": "object",
                "required": ["parser", "query"],
                "properties": {
                    "parser": {
                        "type": "string",
                        "description": "Parser name (e.g., 'FreeAI::Perplexity')",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query to validate",
                    },
                    "options": {
                        "type": "object",
                        "description": "Parameter values to validate (e.g., {'depth': 5, 'sources': 'news'})",
                        "default": {},
                    },
                },
            },
        ),
        Tool(
            name="run_parser",
            description="""
Execute parser. For discovery, use search_parsers first.
Proxy is automatically selected based on parser type.

Args:
- parser: Exact parser name (from search_parsers or get_parser_schema)
- query: Search query
- preset: Preset name (default: 'default')
- async_mode: True for Redis (returns job_id), False for HTTP (waits)
- options: Parser-specific parameters (validate with validate_parser_call first)

Returns:
- async_mode=True: {"status": "queued", "job_id": "..."}
- async_mode=False: {"status": "completed", "result": {...}}
""",
            inputSchema={
                "type": "object",
                "required": ["parser", "query"],
                "properties": {
                    "parser": {
                        "type": "string",
                        "description": "Parser name (e.g., 'SE::Google', 'Net::Whois')",
                    },
                    "query": {
                        "type": "string",
                        "description": "Query string to parse",
                    },
                    "preset": {
                        "type": "string",
                        "description": "Parser preset name",
                        "default": "default",
                    },
                    "config_preset": {
                        "type": "string",
                        "description": "Config preset for thread pool",
                        "default": "default",
                    },
                    "async_mode": {
                        "type": "boolean",
                        "description": "True for Redis queue (non-blocking), False for HTTP (blocking)",
                        "default": True,
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds (for sync mode)",
                        "default": 300,
                    },
                    "options": {
                        "type": "object",
                        "description": "Optional parameter overrides. Use {'from_json': {...}} for complex configs.",
                        "default": {},
                    },
                },
            },
        ),
        Tool(
            name="get_proxy_status",
            description="""
Check current proxy pool status. Returns count of active proxies per checker.
""",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute an ayga_parser MCP tool."""
    if name == "search_parsers":
        result = await _search_parsers(
            query=arguments.get("query", ""),
            category=arguments.get("category"),
            limit=arguments.get("limit", 10),
            min_confidence=arguments.get("min_confidence", 0.5),
        )
        return [TextContent(type="text", text=str(result))]

    elif name == "get_parser_schema":
        result = await _get_parser_schema(
            parser=arguments["parser"],
        )
        return [TextContent(type="text", text=str(result))]

    elif name == "validate_parser_call":
        result = await _validate_parser_call(
            parser=arguments["parser"],
            query=arguments["query"],
            options=arguments.get("options", {}),
        )
        return [TextContent(type="text", text=str(result))]

    elif name == "run_parser":
        result = await _run_parser(
            parser=arguments["parser"],
            query=arguments["query"],
            preset=arguments.get("preset", "default"),
            config_preset=arguments.get("config_preset", "default"),
            async_mode=arguments.get("async_mode", True),
            timeout=arguments.get("timeout", 300),
            options=arguments.get("options"),
        )
        return [TextContent(type="text", text=str(result))]

    elif name == "get_proxy_status":
        result = await _get_proxy_status()
        return [TextContent(type="text", text=str(result))]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def _search_parsers(
    query: str = "",
    category: Optional[str] = None,
    limit: int = 10,
    min_confidence: float = 0.5,
) -> dict:
    """Fuzzy search through all available parsers."""
    try:
        # Get manifest from cache (synchronous load)
        cache = ManifestCache()
        manifest = cache.load()

        if not manifest:
            return {
                "success": False,
                "error": "No manifest found. Run 'ayga_parser parsers sync' first.",
                "results": [],
            }

        # Build search index and search
        index = FuzzySearchIndex(manifest)
        index.build(manifest)
        matches = index.search(query, limit=limit, min_score=min_confidence)

        # Filter by category if specified
        if category:
            matches = [m for m in matches if category.lower() in m.parser.name.lower()]

        # Format results
        results = [
            {
                "name": m.parser.name,
                "description": m.parser.description,
                "category": m.parser.category,
                "confidence": round(m.score, 2),
                "match_type": m.match_type,
            }
            for m in matches
        ]

        # Get cache age
        cache_age_hours = cache.get_age_hours()

        return {
            "success": True,
            "query": query,
            "category_filter": category,
            "total_found": len(results),
            "cache_age_hours": round(cache_age_hours, 2),
            "results": results,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Search failed: {str(e)}",
            "results": [],
        }


async def _get_parser_schema(parser: str) -> dict:
    """Get complete schema for a parser."""
    try:
        # Get manifest from cache (synchronous load)
        cache = ManifestCache()
        manifest = cache.load()

        if not manifest:
            return {
                "success": False,
                "error": "No manifest found. Run 'ayga_parser parsers sync' first.",
            }

        parser_info = manifest.get_parser(parser)

        if not parser_info:
            # Try fuzzy search for suggestions
            index = FuzzySearchIndex(manifest)
            index.build(manifest)
            suggestions = index.search(parser, limit=3)

            return {
                "success": False,
                "error": f"Parser '{parser}' not found.",
                "suggestions": [s.parser.name for s in suggestions],
                "hint": "Use search_parsers() to find the correct parser name.",
            }

        # Build schema response from parameters
        parameters = {}
        for param_name, param_schema in parser_info.parameters.items():
            parameters[param_name] = {
                "type": param_schema.type,
                "description": param_schema.description,
                "required": param_schema.required,
                "default": param_schema.default,
            }
            if param_schema.min is not None:
                parameters[param_name]["min"] = param_schema.min
            if param_schema.max is not None:
                parameters[param_name]["max"] = param_schema.max
            if param_schema.enum is not None:
                parameters[param_name]["enum"] = param_schema.enum

        return {
            "success": True,
            "name": parser_info.name,
            "description": parser_info.description,
            "category": parser_info.category,
            "parameters": parameters,
            "presets": parser_info.presets,
            "keywords": parser_info.keywords,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get schema: {str(e)}",
        }


async def _validate_parser_call(
    parser: str,
    query: str,
    options: dict[str, Any],
) -> dict:
    """Validate parameters before execution."""
    try:
        # Get manifest from cache (synchronous load)
        cache = ManifestCache()
        manifest = cache.load()

        if not manifest:
            return {
                "success": False,
                "valid": False,
                "error": "No manifest found. Run 'ayga_parser parsers sync' first.",
            }

        parser_info = manifest.get_parser(parser)

        if not parser_info:
            index = FuzzySearchIndex(manifest)
            index.build(manifest)
            suggestions = index.search(parser, limit=3)
            return {
                "success": False,
                "valid": False,
                "error": f"Parser '{parser}' not found.",
                "suggestions": [s.parser.name for s in suggestions],
            }

        # Validate
        errors = []
        warnings = []
        transformed_options = []

        # Validate query
        if not query or not query.strip():
            errors.append("Query is required and cannot be empty")

        # Get parameter schemas
        param_schemas = parser_info.parameters

        # Validate each option
        for key, value in options.items():
            if key not in param_schemas:
                errors.append(f"Unknown parameter: {key}")
                continue

            schema = param_schemas[key]
            transformed_value = value

            # Type validation
            if schema.type == "integer":
                try:
                    transformed_value = int(value)
                except (ValueError, TypeError):
                    errors.append(f"Parameter '{key}' must be an integer, got: {value}")
                    continue

                # Range validation
                if schema.min is not None and transformed_value < schema.min:
                    errors.append(f"Parameter '{key}' must be >= {schema.min}, got: {transformed_value}")
                if schema.max is not None and transformed_value > schema.max:
                    errors.append(f"Parameter '{key}' must be <= {schema.max}, got: {transformed_value}")

            elif schema.type == "float":
                try:
                    transformed_value = float(value)
                except (ValueError, TypeError):
                    errors.append(f"Parameter '{key}' must be a number, got: {value}")
                    continue

                if schema.min is not None and transformed_value < schema.min:
                    errors.append(f"Parameter '{key}' must be >= {schema.min}, got: {transformed_value}")
                if schema.max is not None and transformed_value > schema.max:
                    errors.append(f"Parameter '{key}' must be <= {schema.max}, got: {transformed_value}")

            elif schema.type == "boolean":
                if isinstance(value, str):
                    transformed_value = value.lower() in ("true", "1", "yes", "on")
                else:
                    transformed_value = bool(value)

            elif schema.enum is not None:
                if str(value) not in [str(v) for v in schema.enum]:
                    errors.append(f"Parameter '{key}' must be one of {schema.enum}, got: {value}")

            transformed_options.append({
                "id": key,
                "value": transformed_value,
            })

        # Check required parameters
        for param_name, param_schema in param_schemas.items():
            if param_schema.required and param_name not in options:
                errors.append(f"Required parameter '{param_name}' is missing")

        valid = len(errors) == 0

        return {
            "success": True,
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "transformed_payload": {
                "parser": parser,
                "query": query,
                "options": transformed_options,
            } if valid else {},
        }

    except Exception as e:
        return {
            "success": False,
            "valid": False,
            "error": f"Validation failed: {str(e)}",
        }


async def _run_parser(
    parser: str,
    query: str,
    preset: str = "default",
    config_preset: str = "default",
    async_mode: bool = True,
    timeout: int = 300,
    options: Optional[dict] = None,
) -> dict:
    """Execute parsing job via ayga_parser."""
    config = AygaParserConfig()

    # Extract options list if provided
    options_list = None
    if options:
        if "from_json" in options:
            options_list = options["from_json"]
        elif isinstance(options, list):
            options_list = options
        elif isinstance(options, dict):
            # Convert simple dict to options list format
            options_list = [{"id": k, "value": v} for k, v in options.items()]

    if options_list is None:
        options_list = []

    options_list = merge_with_proxy(parser, options_list)

    if async_mode:
        # Async mode: Redis queue (non-blocking)
        client = AygaParserRedisClient(
            redis_host=config.redis_host,
            redis_port=config.redis_port,
            redis_queue=config.redis_queue,
            redis_password=config.redis_password.get_secret_value() if config.redis_password else None,
            password=config.get_password(),
        )

        try:
            result_queue = await client.push(
                parser=parser,
                query=query,
                preset=preset,
                config_preset=config_preset,
                options=options_list,
            )
            return {
                "success": True,
                "status": "queued",
                "job_id": result_queue,
                "message": f"Job queued. Use result_queue='{result_queue}' to retrieve results via Redis BLPOP.",
            }
        except Exception as e:
            return {
                "success": False,
                "status": "error",
                "error": str(e),
            }
        finally:
            await client.close()
    else:
        # Sync mode: HTTP direct (blocking)
        client = AygaParserHttpClient(config)

        try:
            await client.connect()
            result = await client.one_request(
                parser=parser,
                query=query,
                preset=preset,
                config_preset=config_preset,
                options=options_list,
                timeout=timeout,
            )
            return {
                "success": True,
                "status": "completed",
                "result": result,
            }
        except Exception as e:
            return {
                "success": False,
                "status": "error",
                "error": str(e),
            }
        finally:
            await client.close()

async def _get_proxy_status() -> dict:
    """Check current proxy pool status."""
    config = AygaParserConfig()
    client = AygaParserHttpClient(config)
    
    try:
        await client.connect()
        result = await client.get_proxies()
        return result
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}
    finally:
        await client.close()


# Run server entry point
def main():
    """Run the MCP server."""
    import asyncio
    from mcp.server.stdio import stdio_server

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await mcp.run(
                read_stream,
                write_stream,
                mcp.create_initialization_options(),
            )

    asyncio.run(run())


if __name__ == "__main__":
    main()
