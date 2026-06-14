"""Tests for MCP server."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from ayga_cli.mcp.server import (
    list_tools,
    call_tool,
    _search_parsers,
    _get_parser_schema,
    _validate_parser_call,
    _run_parser,
)
from ayga_cli.manifest import ParserInfo, ParameterSchema, Manifest, FuzzySearchIndex, ParserMatch


class TestListTools:
    """Test suite for list_tools."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_tools(self):
        """Test that list_tools returns available tools."""
        tools = await list_tools()

        assert len(tools) == 4

        tool_names = [t.name for t in tools]
        assert "search_parsers" in tool_names
        assert "get_parser_schema" in tool_names
        assert "validate_parser_call" in tool_names
        assert "run_parser" in tool_names

    @pytest.mark.asyncio
    async def test_search_parsers_tool_schema(self):
        """Test search_parsers tool schema."""
        tools = await list_tools()
        search_tool = next(t for t in tools if t.name == "search_parsers")

        assert search_tool.name == "search_parsers"
        assert "fuzzy" in search_tool.description.lower() or "PRIMARY" in search_tool.description
        assert "query" in search_tool.inputSchema["properties"]
        assert "category" in search_tool.inputSchema["properties"]
        assert "limit" in search_tool.inputSchema["properties"]
        assert "min_confidence" in search_tool.inputSchema["properties"]

    @pytest.mark.asyncio
    async def test_get_parser_schema_tool_schema(self):
        """Test get_parser_schema tool schema."""
        tools = await list_tools()
        schema_tool = next(t for t in tools if t.name == "get_parser_schema")

        assert schema_tool.name == "get_parser_schema"
        assert "parser" in schema_tool.inputSchema["required"]
        assert "parser" in schema_tool.inputSchema["properties"]

    @pytest.mark.asyncio
    async def test_validate_parser_call_tool_schema(self):
        """Test validate_parser_call tool schema."""
        tools = await list_tools()
        validate_tool = next(t for t in tools if t.name == "validate_parser_call")

        assert validate_tool.name == "validate_parser_call"
        assert "parser" in validate_tool.inputSchema["required"]
        assert "query" in validate_tool.inputSchema["required"]
        assert "options" in validate_tool.inputSchema["properties"]

    @pytest.mark.asyncio
    async def test_run_parser_tool_schema(self):
        """Test run_parser tool schema."""
        tools = await list_tools()
        run_tool = next(t for t in tools if t.name == "run_parser")

        assert run_tool.name == "run_parser"
        assert "parser" in run_tool.inputSchema["required"]
        assert "query" in run_tool.inputSchema["required"]
        assert "async_mode" in run_tool.inputSchema["properties"]
        assert "options" in run_tool.inputSchema["properties"]


class TestCallTool:
    """Test suite for call_tool."""

    @pytest.mark.asyncio
    async def test_call_search_parsers(self):
        """Test calling search_parsers via call_tool."""
        with patch("ayga_cli.mcp.server._search_parsers") as mock_search:
            mock_search.return_value = {"success": True, "results": []}

            result = await call_tool("search_parsers", {"query": "test"})

            assert len(result) == 1
            mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_get_parser_schema(self):
        """Test calling get_parser_schema via call_tool."""
        with patch("ayga_cli.mcp.server._get_parser_schema") as mock_schema:
            mock_schema.return_value = {"success": True, "name": "Test"}

            result = await call_tool("get_parser_schema", {"parser": "SE::Google"})

            assert len(result) == 1
            mock_schema.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_validate_parser_call(self):
        """Test calling validate_parser_call via call_tool."""
        with patch("ayga_cli.mcp.server._validate_parser_call") as mock_validate:
            mock_validate.return_value = {"success": True, "valid": True}

            result = await call_tool("validate_parser_call", {
                "parser": "SE::Google",
                "query": "test",
            })

            assert len(result) == 1
            mock_validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_run_parser(self):
        """Test calling run_parser via call_tool."""
        with patch("ayga_cli.mcp.server._run_parser") as mock_run:
            mock_run.return_value = {"status": "queued", "job_id": "test_queue"}

            result = await call_tool("run_parser", {
                "parser": "SE::Google",
                "query": "test",
            })

            assert len(result) == 1
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_unknown_tool_raises(self):
        """Test calling unknown tool raises error."""
        with pytest.raises(ValueError) as exc_info:
            await call_tool("unknown_tool", {})
        assert "Unknown tool" in str(exc_info.value)


class TestSearchParsers:
    """Test suite for _search_parsers."""

    @pytest.mark.asyncio
    async def test_search_parsers_success(self):
        """Test successful parser search."""
        mock_parser = ParserInfo(
            name="SE::Google",
            description="Google search parser",
            category="SE",
            keywords=["google", "search", "se::google"],
        )
        manifest = Manifest(parsers={"SE::Google": mock_parser})

        with patch("ayga_cli.mcp.server.ManifestCache") as MockCache, \
             patch("ayga_cli.mcp.server.FuzzySearchIndex") as MockIndex:
            mock_cache = MagicMock()
            mock_cache.load.return_value = manifest
            mock_cache.get_age_hours.return_value = 0.5
            MockCache.return_value = mock_cache

            mock_index = MagicMock()
            mock_index.search.return_value = [
                ParserMatch(parser=mock_parser, score=0.95, match_type="exact", matched_term="SE::Google")
            ]
            MockIndex.return_value = mock_index

            result = await _search_parsers(query="Google")

            assert result["success"] is True
            assert len(result["results"]) == 1
            assert result["results"][0]["name"] == "SE::Google"

    @pytest.mark.asyncio
    async def test_search_parsers_by_category(self):
        """Test parser search filtered by category."""
        mock_parser = ParserInfo(
            name="Net::Whois",
            description="WHOIS lookup parser",
            category="Net",
            keywords=["whois", "net", "domain"],
        )
        manifest = Manifest(parsers={"Net::Whois": mock_parser})

        with patch("ayga_cli.mcp.server.ManifestCache") as MockCache, \
             patch("ayga_cli.mcp.server.FuzzySearchIndex") as MockIndex:
            mock_cache = MagicMock()
            mock_cache.load.return_value = manifest
            mock_cache.get_age_hours.return_value = 0.5
            MockCache.return_value = mock_cache

            mock_index = MagicMock()
            mock_index.search.return_value = [
                ParserMatch(parser=mock_parser, score=0.9, match_type="substring", matched_term="whois")
            ]
            MockIndex.return_value = mock_index

            result = await _search_parsers(query="whois", category="Net")

            assert result["success"] is True
            assert len(result["results"]) == 1
            assert result["results"][0]["name"] == "Net::Whois"

    @pytest.mark.asyncio
    async def test_search_parsers_empty_result(self):
        """Test parser search with no matches."""
        manifest = Manifest(parsers={})

        with patch("ayga_cli.mcp.server.ManifestCache") as MockCache, \
             patch("ayga_cli.mcp.server.FuzzySearchIndex") as MockIndex:
            mock_cache = MagicMock()
            mock_cache.load.return_value = manifest
            mock_cache.get_age_hours.return_value = 0.5
            MockCache.return_value = mock_cache

            mock_index = MagicMock()
            mock_index.search.return_value = []
            MockIndex.return_value = mock_index

            result = await _search_parsers(query="NonExistent")

            assert result["success"] is True
            assert len(result["results"]) == 0

    @pytest.mark.asyncio
    async def test_search_parsers_limits_results(self):
        """Test that search_parsers respects limit."""
        mock_parsers = [
            ParserInfo(name=f"Parser{i}", description=f"Desc{i}", category="Cat", keywords=[])
            for i in range(25)
        ]
        manifest = Manifest(parsers={p.name: p for p in mock_parsers})

        with patch("ayga_cli.mcp.server.ManifestCache") as MockCache, \
             patch("ayga_cli.mcp.server.FuzzySearchIndex") as MockIndex:
            mock_cache = MagicMock()
            mock_cache.load.return_value = manifest
            mock_cache.get_age_hours.return_value = 0.5
            MockCache.return_value = mock_cache

            mock_index = MagicMock()
            mock_index.search.return_value = [
                ParserMatch(parser=p, score=0.8, match_type="keyword", matched_term=p.name)
                for p in mock_parsers[:10]
            ]
            MockIndex.return_value = mock_index

            result = await _search_parsers(limit=10)

            assert result["success"] is True
            assert len(result["results"]) == 10


class TestGetParserSchema:
    """Test suite for _get_parser_schema."""

    @pytest.mark.asyncio
    async def test_get_parser_schema_success(self):
        """Test getting parser schema successfully."""
        mock_parser = ParserInfo(
            name="FreeAI::Perplexity",
            description="AI-powered search",
            category="FreeAI",
            parameters={
                "depth": ParameterSchema(
                    type="integer",
                    description="Number of related questions",
                    required=False,
                    default=3,
                    min=1,
                    max=10,
                ),
            },
            presets=["default", "academic"],
        )
        manifest = Manifest(parsers={"FreeAI::Perplexity": mock_parser})

        with patch("ayga_cli.mcp.server.ManifestCache") as MockCache:
            mock_cache = MagicMock()
            mock_cache.load.return_value = manifest
            MockCache.return_value = mock_cache

            result = await _get_parser_schema(parser="FreeAI::Perplexity")

            assert result["success"] is True
            assert result["name"] == "FreeAI::Perplexity"
            assert "depth" in result["parameters"]
            assert result["parameters"]["depth"]["type"] == "integer"
            assert result["parameters"]["depth"]["min"] == 1
            assert result["parameters"]["depth"]["max"] == 10

    @pytest.mark.asyncio
    async def test_get_parser_schema_not_found(self):
        """Test getting schema for non-existent parser."""
        manifest = Manifest(parsers={})

        with patch("ayga_cli.mcp.server.ManifestCache") as MockCache, \
             patch("ayga_cli.mcp.server.FuzzySearchIndex") as MockIndex:
            mock_cache = MagicMock()
            mock_cache.load.return_value = manifest
            MockCache.return_value = mock_cache

            mock_index = MagicMock()
            mock_index.search.return_value = []
            MockIndex.return_value = mock_index

            result = await _get_parser_schema(parser="NonExistent")

            assert result["success"] is False
            assert "not found" in result["error"].lower()


class TestValidateParserCall:
    """Test suite for _validate_parser_call."""

    @pytest.mark.asyncio
    async def test_validate_parser_call_success(self):
        """Test successful parameter validation."""
        mock_parser = ParserInfo(
            name="SE::Google",
            description="Google search",
            category="SE",
            parameters={
                "depth": ParameterSchema(
                    type="integer",
                    description="Search depth",
                    required=False,
                    default=1,
                    min=1,
                    max=10,
                ),
            },
        )
        manifest = Manifest(parsers={"SE::Google": mock_parser})

        with patch("ayga_cli.mcp.server.ManifestCache") as MockCache:
            mock_cache = MagicMock()
            mock_cache.load.return_value = manifest
            MockCache.return_value = mock_cache

            result = await _validate_parser_call(
                parser="SE::Google",
                query="test query",
                options={"depth": 3},
            )

            assert result["success"] is True
            assert result["valid"] is True
            assert len(result["errors"]) == 0
            assert "transformed_payload" in result

    @pytest.mark.asyncio
    async def test_validate_parser_call_invalid_type(self):
        """Test validation with invalid parameter type."""
        mock_parser = ParserInfo(
            name="SE::Google",
            description="Google search",
            category="SE",
            parameters={
                "depth": ParameterSchema(
                    type="integer",
                    description="Search depth",
                    required=False,
                    default=1,
                ),
            },
        )
        manifest = Manifest(parsers={"SE::Google": mock_parser})

        with patch("ayga_cli.mcp.server.ManifestCache") as MockCache:
            mock_cache = MagicMock()
            mock_cache.load.return_value = manifest
            MockCache.return_value = mock_cache

            result = await _validate_parser_call(
                parser="SE::Google",
                query="test",
                options={"depth": "invalid"},
            )

            assert result["success"] is True
            assert result["valid"] is False
            assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_parser_call_out_of_range(self):
        """Test validation with out-of-range parameter."""
        mock_parser = ParserInfo(
            name="SE::Google",
            description="Google search",
            category="SE",
            parameters={
                "depth": ParameterSchema(
                    type="integer",
                    description="Search depth",
                    required=False,
                    default=1,
                    min=1,
                    max=5,
                ),
            },
        )
        manifest = Manifest(parsers={"SE::Google": mock_parser})

        with patch("ayga_cli.mcp.server.ManifestCache") as MockCache:
            mock_cache = MagicMock()
            mock_cache.load.return_value = manifest
            MockCache.return_value = mock_cache

            result = await _validate_parser_call(
                parser="SE::Google",
                query="test",
                options={"depth": 10},
            )

            assert result["success"] is True
            assert result["valid"] is False
            assert any("10" in e and "5" in e for e in result["errors"])


class TestRunParser:
    """Test suite for _run_parser."""

    @pytest.mark.asyncio
    async def test_run_parser_async_mode(self):
        """Test running parser in async mode."""
        with patch("ayga_cli.mcp.server.ayga-parserRedisClient") as MockRedis:
            mock_client = AsyncMock()
            mock_client.push.return_value = "test_queue_123"
            MockRedis.return_value = mock_client

            result = await _run_parser(
                parser="SE::Google",
                query="test",
                async_mode=True,
            )

            assert result["success"] is True
            assert result["status"] == "queued"
            assert "job_id" in result

    @pytest.mark.asyncio
    async def test_run_parser_sync_mode(self):
        """Test running parser in sync mode."""
        with patch("ayga_cli.mcp.server.ayga-parserHttpClient") as MockHttp:
            mock_client = AsyncMock()
            mock_client.one_request.return_value = {"data": {"results": []}}
            MockHttp.return_value = mock_client

            result = await _run_parser(
                parser="SE::Google",
                query="test",
                async_mode=False,
            )

            assert result["success"] is True
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_run_parser_with_options(self):
        """Test running parser with options."""
        with patch("ayga_cli.mcp.server.ayga-parserRedisClient") as MockRedis:
            mock_client = AsyncMock()
            mock_client.push.return_value = "test_queue"
            MockRedis.return_value = mock_client

            result = await _run_parser(
                parser="SE::Google",
                query="test",
                async_mode=True,
                options={"depth": 5},
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_run_parser_with_from_json_options(self):
        """Test running parser with from_json options."""
        with patch("ayga_cli.mcp.server.ayga-parserRedisClient") as MockRedis:
            mock_client = AsyncMock()
            mock_client.push.return_value = "test_queue"
            MockRedis.return_value = mock_client

            result = await _run_parser(
                parser="SE::Google",
                query="test",
                async_mode=True,
                options={"from_json": [{"id": "depth", "value": 5}]},
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_run_parser_with_preset(self):
        """Test running parser with custom preset."""
        with patch("ayga_cli.mcp.server.ayga-parserRedisClient") as MockRedis:
            mock_client = AsyncMock()
            mock_client.push.return_value = "test_queue"
            MockRedis.return_value = mock_client

            result = await _run_parser(
                parser="SE::Google",
                query="test",
                preset="deep",
                async_mode=True,
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_run_parser_with_timeout(self):
        """Test running parser with custom timeout."""
        with patch("ayga_cli.mcp.server.ayga-parserHttpClient") as MockHttp:
            mock_client = AsyncMock()
            mock_client.one_request.return_value = {"data": {"results": []}}
            MockHttp.return_value = mock_client

            result = await _run_parser(
                parser="SE::Google",
                query="test",
                async_mode=False,
                timeout=60,
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_run_parser_error_handling(self):
        """Test error handling in run_parser."""
        with patch("ayga_cli.mcp.server.ayga-parserRedisClient") as MockRedis:
            mock_client = AsyncMock()
            mock_client.push.side_effect = Exception("Connection failed")
            MockRedis.return_value = mock_client

            result = await _run_parser(
                parser="SE::Google",
                query="test",
                async_mode=True,
            )

            assert result["success"] is False
            assert "error" in result
