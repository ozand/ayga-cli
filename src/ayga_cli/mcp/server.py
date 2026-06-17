"""MCP server for ayga data access — provides source-based data fetching"""

from typing import Any, Optional

from mcp.server import Server
from mcp.types import TextContent, Tool

from ayga_cli.client.redis import AygaParserRedisClient
from ayga_cli.config import AygaParserConfig

# Initialize MCP server
mcp = Server(
    "ayga_parser-mcp-v2",
    instructions="""
Universal data collection tool.

WORKFLOW FOR AGENTS:
1. DISCOVER: Call list_sources() to find available sources.
2. EXECUTE: Call fetch_data(source, query) to fetch data.
"""
)

@mcp.list_tools()
async def list_tools() -> list[Tool]:
    """List available ayga_parser MCP tools."""
    return [
        Tool(
            name="fetch_data",
            description="Fetch data from a named source. Available sources can be listed with list_sources.",
            inputSchema={
                "type": "object",
                "required": ["source", "query"],
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Source name (e.g. web-search, ai-answer). Use list_sources to see available sources.",
                    },
                    "query": {
                        "type": "string",
                        "description": "The query or URL to fetch data for",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum seconds to wait for result",
                        "default": 300,
                    },
                },
            },
        ),
        Tool(
            name="list_sources",
            description="List available data sources",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]

@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute an ayga_parser MCP tool."""
    if name == "fetch_data":
        result = await _fetch_data(
            source=arguments["source"],
            query=arguments["query"],
            timeout=arguments.get("timeout", 300),
        )
        return [TextContent(type="text", text=str(result))]

    elif name == "list_sources":
        result = await _list_sources()
        return [TextContent(type="text", text=str(result))]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def _fetch_data(source: str, query: str, timeout: int = 300) -> dict:
    config = AygaParserConfig()
    client = AygaParserRedisClient(
        redis_host=config.redis_host,
        redis_port=config.redis_port,
        redis_queue=config.redis_queue,
        redis_password=config.redis_password.get_secret_value() if config.redis_password else None,
        password=config.get_password(),
    )
    try:
        result_queue = await client.push(source, query)
        result = await client.pop(result_queue, timeout)
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

async def _list_sources() -> dict:
    config = AygaParserConfig()
    client = AygaParserRedisClient(
        redis_host=config.redis_host,
        redis_port=config.redis_port,
        redis_queue=config.redis_queue,
        redis_password=config.redis_password.get_secret_value() if config.redis_password else None,
        password=config.get_password(),
    )
    try:
        sources = await client.get_sources()
        if not sources:
            return {"message": "No sources configured. Contact administrator."}
        return {"sources": sources}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
    finally:
        await client.close()


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
