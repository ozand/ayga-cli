"""Tests for MCP server."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from ayga_cli.mcp.server import (
    list_tools,
    call_tool,
    _fetch_data,
    _list_sources,
)

class TestListTools:
    """Test suite for list_tools."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_tools(self):
        """Test that list_tools returns available tools."""
        tools = await list_tools()
        assert len(tools) == 2

        tool_names = [t.name for t in tools]
        assert "fetch_data" in tool_names
        assert "list_sources" in tool_names

    @pytest.mark.asyncio
    async def test_fetch_data_tool_schema(self):
        """Test fetch_data tool schema."""
        tools = await list_tools()
        fetch_tool = next(t for t in tools if t.name == "fetch_data")

        assert fetch_tool.name == "fetch_data"
        assert "source" in fetch_tool.inputSchema["required"]
        assert "query" in fetch_tool.inputSchema["required"]
        assert "source" in fetch_tool.inputSchema["properties"]
        assert "query" in fetch_tool.inputSchema["properties"]
        assert "timeout" in fetch_tool.inputSchema["properties"]

    @pytest.mark.asyncio
    async def test_list_sources_tool_schema(self):
        """Test list_sources tool schema."""
        tools = await list_tools()
        list_tool = next(t for t in tools if t.name == "list_sources")

        assert list_tool.name == "list_sources"
        assert list_tool.inputSchema["properties"] == {}

class TestCallTool:
    """Test suite for call_tool."""

    @pytest.mark.asyncio
    async def test_call_fetch_data(self):
        """Test calling fetch_data via call_tool."""
        with patch("ayga_cli.mcp.server._fetch_data") as mock_fetch:
            mock_fetch.return_value = {"success": True, "result": "test"}

            result = await call_tool("fetch_data", {"source": "web", "query": "test"})

            assert len(result) == 1
            mock_fetch.assert_called_once_with(source="web", query="test", timeout=300)

    @pytest.mark.asyncio
    async def test_call_list_sources(self):
        """Test calling list_sources via call_tool."""
        with patch("ayga_cli.mcp.server._list_sources") as mock_list:
            mock_list.return_value = {"sources": ["web"]}

            result = await call_tool("list_sources", {})

            assert len(result) == 1
            mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_unknown_tool_raises(self):
        """Test calling unknown tool raises error."""
        with pytest.raises(ValueError) as exc_info:
            await call_tool("unknown_tool", {})
        assert "Unknown tool" in str(exc_info.value)

class TestFetchData:
    """Test suite for _fetch_data."""

    @pytest.mark.asyncio
    async def test_fetch_data_success(self):
        """Test successful fetch_data."""
        with patch("ayga_cli.mcp.server.AygaParserRedisClient") as MockRedis:
            mock_client = AsyncMock()
            mock_client.push.return_value = "test_queue"
            mock_client.pop.return_value = {"data": "test"}
            MockRedis.return_value = mock_client

            result = await _fetch_data("web", "test", timeout=10)

            assert result["success"] is True
            assert result["result"] == {"data": "test"}
            mock_client.push.assert_called_once_with("web", "test")
            mock_client.pop.assert_called_once_with("test_queue", 10)

class TestListSources:
    """Test suite for _list_sources."""

    @pytest.mark.asyncio
    async def test_list_sources_success(self):
        """Test successful list_sources."""
        with patch("ayga_cli.mcp.server.AygaParserRedisClient") as MockRedis:
            mock_client = AsyncMock()
            mock_client.get_sources.return_value = ["web", "ai"]
            MockRedis.return_value = mock_client

            result = await _list_sources()

            assert "sources" in result
            assert result["sources"] == ["web", "ai"]

    @pytest.mark.asyncio
    async def test_list_sources_empty(self):
        """Test list_sources when empty."""
        with patch("ayga_cli.mcp.server.AygaParserRedisClient") as MockRedis:
            mock_client = AsyncMock()
            mock_client.get_sources.return_value = []
            MockRedis.return_value = mock_client

            result = await _list_sources()

            assert "message" in result
            assert "No sources configured" in result["message"]
