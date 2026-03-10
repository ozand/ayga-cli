"""Tests for A-Parser HTTP client."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from aparser_cli.client.http import AParserHttpClient
from aparser_cli.config import AParserConfig
from aparser_cli.exceptions import (
    AParserAPIError,
    AParserAuthError,
    AParserHTTPError,
    AParserTimeoutError,
    AParserValidationError,
)


class TestAParserHttpClient:
    """Test suite for AParserHttpClient."""

    @pytest.mark.asyncio
    async def test_init_with_config(self, mock_config):
        """Test client initialization with config."""
        client = AParserHttpClient(config=mock_config)
        assert client.config == mock_config
        assert client.timeout == mock_config.default_timeout

    @pytest.mark.asyncio
    async def test_init_default_config(self):
        """Test client initialization with default config."""
        with patch("aparser_cli.client.http.AParserConfig") as MockConfig:
            mock_config = MagicMock()
            mock_config.default_timeout = 300
            mock_config.get_http_basic_auth.return_value = None
            MockConfig.return_value = mock_config
            client = AParserHttpClient()
            assert client.config is not None

    @pytest.mark.asyncio
    async def test_connect(self, mock_config):
        """Test client connection."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            
            assert client._client is not None
            MockClient.assert_called_once()
            assert MockClient.call_args.kwargs.get("auth") is not None

    @pytest.mark.asyncio
    async def test_close(self, mock_config):
        """Test client close."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            await client.close()
            
            mock_client.aclose.assert_called_once()
            assert client._client is None

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_config):
        """Test async context manager."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            async with AParserHttpClient(config=mock_config) as client:
                assert client._client is not None
            
            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_connected_not_connected(self, mock_config):
        """Test _ensure_connected raises error when not connected."""
        client = AParserHttpClient(config=mock_config)
        with pytest.raises(AParserHTTPError) as exc_info:
            client._ensure_connected()
        assert "Client not connected" in str(exc_info.value)


class TestAParserHttpClientRequests:
    """Test suite for HTTP client requests."""

    @pytest.fixture
    async def connected_client(self, mock_config, mock_httpx_client):
        """Create a connected client fixture."""
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            yield client
            await client.close()

    @pytest.mark.asyncio
    async def test_ping_success(self, mock_config, mock_httpx_client):
        """Test successful ping."""
        mock_httpx_client.post.return_value.json.return_value = {"success": 1, "data": "pong"}
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.ping()
            
            assert result == True  # API returns 1, not Python True
            mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_ping_failure(self, mock_config, mock_httpx_client):
        """Test ping with API error."""
        mock_httpx_client.post.return_value.json.return_value = {"success": 0, "error": "Auth failed"}
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            
            with pytest.raises(AParserAPIError):
                await client.ping()

    @pytest.mark.asyncio
    async def test_one_request_success(self, mock_config, mock_httpx_client):
        """Test oneRequest method."""
        mock_httpx_client.post.return_value.json.return_value = {
            "success": 1,
            "data": {"results": ["test"]},
        }
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.one_request(
                parser="SE::Google",
                query="test",
                preset="default",
            )
            
            assert result["success"] == 1
            assert result["data"]["results"] == ["test"]

    @pytest.mark.asyncio
    async def test_one_request_validation_empty_parser(self, mock_config):
        """Test oneRequest with empty parser."""
        client = AParserHttpClient(config=mock_config)
        
        with pytest.raises(AParserValidationError) as exc_info:
            await client.one_request(parser="", query="test")
        assert "Parser name is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_one_request_validation_empty_query(self, mock_config):
        """Test oneRequest with empty query."""
        client = AParserHttpClient(config=mock_config)
        
        with pytest.raises(AParserValidationError) as exc_info:
            await client.one_request(parser="SE::Google", query="")
        assert "Query is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_parsers_list(self, mock_config, mock_httpx_client):
        """Test getParsersList method."""
        mock_httpx_client.post.return_value.json.return_value = {
            "success": 1,
            "data": [
                {"name": "SE::Google", "description": "Google parser", "category": "SE"},
                {"name": "Net::Whois", "description": "Whois parser", "category": "Net"},
            ],
        }
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_parsers_list()
            
            assert len(result) == 2
            assert result[0]["name"] == "SE::Google"
            assert result[1]["name"] == "Net::Whois"

    @pytest.mark.asyncio
    async def test_get_parsers_list_falls_back_to_static_manifest(self, mock_config, mock_httpx_client):
        """Test parser list fallback when API action is unsupported."""
        mock_httpx_client.post.return_value.json.return_value = {
            "success": 0,
            "msg": "Unknown action",
        }

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_parsers_list()

            assert any(parser["name"] == "SE::Google" for parser in result)

    @pytest.mark.asyncio
    async def test_get_parser_info(self, mock_config, mock_httpx_client):
        """Test getParserInfo method."""
        mock_httpx_client.post.return_value.json.return_value = {
            "success": 1,
            "data": {"name": "SE::Google", "options": []},
        }
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_parser_info("SE::Google")
            
            assert result["name"] == "SE::Google"

    @pytest.mark.asyncio
    async def test_get_parser_info_validation(self, mock_config):
        """Test getParserInfo with empty parser name."""
        client = AParserHttpClient(config=mock_config)
        
        with pytest.raises(AParserValidationError) as exc_info:
            await client.get_parser_info("")
        assert "Parser name is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_tasks_list(self, mock_config, mock_httpx_client):
        """Test getTasksList method."""
        mock_httpx_client.post.return_value.json.return_value = {
            "success": 1,
            "data": [{"id": "task1", "status": "running"}],
        }
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_tasks_list()
            
            assert len(result) == 1
            assert result[0]["id"] == "task1"

    @pytest.mark.asyncio
    async def test_get_task_info(self, mock_config, mock_httpx_client):
        """Test getTaskInfo method."""
        mock_httpx_client.post.return_value.json.return_value = {
            "success": 1,
            "data": {"id": "task1", "progress": 50},
        }
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_task_info("task1")
            
            assert result["id"] == "task1"
            assert result["progress"] == 50

    @pytest.mark.asyncio
    async def test_cancel_task(self, mock_config, mock_httpx_client):
        """Test cancelTask method."""
        mock_httpx_client.post.return_value.json.return_value = {"success": 1}
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.cancel_task("task1")
            
            assert result == True  # API returns 1, not Python True

    @pytest.mark.asyncio
    async def test_get_presets_list(self, mock_config, mock_httpx_client):
        """Test getPresetsList method."""
        mock_httpx_client.post.return_value.json.return_value = {
            "success": 1,
            "data": [{"name": "default", "parser": "SE::Google"}],
        }
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_presets_list()
            
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_config_presets_list(self, mock_config, mock_httpx_client):
        """Test getConfigPresetsList method."""
        mock_httpx_client.post.return_value.json.return_value = {
            "success": 1,
            "data": [{"name": "default"}],
        }
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_config_presets_list()
            
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_results(self, mock_config, mock_httpx_client):
        """Test getResults method."""
        mock_httpx_client.post.return_value.json.return_value = {
            "success": 1,
            "data": {"results": ["result1", "result2"]},
        }
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_results("task1")
            
            assert "results" in result


class TestAParserHttpClientErrors:
    """Test suite for HTTP client error handling."""

    @pytest.mark.asyncio
    async def test_timeout_error(self, mock_config):
        """Test timeout error handling."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Connection timeout")
            MockClient.return_value = mock_client
            
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            
            with pytest.raises(AParserTimeoutError) as exc_info:
                await client.ping()
            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_http_status_error(self, mock_config):
        """Test HTTP status error handling."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            
            error = httpx.HTTPStatusError(
                "Server error",
                request=MagicMock(),
                response=mock_response,
            )
            mock_client.post.side_effect = error
            MockClient.return_value = mock_client
            
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            
            with pytest.raises(AParserHTTPError) as exc_info:
                await client.ping()
            assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, mock_config):
        """Test invalid JSON response handling."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_response.status_code = 200
            mock_response.text = "not valid json"
            mock_client.post.return_value = mock_response
            MockClient.return_value = mock_client
            
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            
            with pytest.raises(AParserHTTPError) as exc_info:
                await client.ping()
            assert "Invalid JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_auth_error_no_password(self, mock_config):
        """Test authentication error when password not configured."""
        mock_config.get_password.return_value = None
        
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            
            client = AParserHttpClient(config=mock_config)
            await client.connect()
            
            with pytest.raises(AParserAuthError) as exc_info:
                await client.ping()
            assert "password not configured" in str(exc_info.value)
