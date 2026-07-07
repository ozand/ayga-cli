"""Tests for ayga_parser HTTP client."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from ayga_cli.client.http import AygaParserHttpClient
from ayga_cli.config import AygaParserConfig
from ayga_cli.exceptions import (
    AygaParserAPIError,
    AygaParserAuthError,
    AygaParserHTTPError,
    AygaParserTimeoutError,
    AygaParserValidationError,
)


class TestAygaParserHttpClient:
    """Test suite for AygaParserHttpClient."""

    @pytest.mark.asyncio
    async def test_init_with_config(self, mock_config):
        """Test client initialization with config."""
        client = AygaParserHttpClient(config=mock_config)
        assert client.config == mock_config
        assert client.timeout == mock_config.default_timeout

    @pytest.mark.asyncio
    async def test_init_default_config(self):
        """Test client initialization with default config."""
        with patch("ayga_cli.client.http.AygaParserConfig") as MockConfig:
            mock_config = MagicMock()
            mock_config.default_timeout = 300
            mock_config.get_http_basic_auth.return_value = None
            MockConfig.return_value = mock_config
            client = AygaParserHttpClient()
            assert client.config is not None

    @pytest.mark.asyncio
    async def test_connect(self, mock_config):
        """Test client connection."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()

            assert client._client is not None
            assert client._api_client is not None
            # One client for http_url (native API), one for api_url (Redis Wrapper REST API)
            assert MockClient.call_count == 2
            assert MockClient.call_args_list[0].kwargs.get("auth") is not None
            assert MockClient.call_args_list[1].kwargs["headers"]["X-API-Key"] == "test_password"

    @pytest.mark.asyncio
    async def test_close(self, mock_config):
        """Test client close."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            await client.close()

            assert mock_client.aclose.call_count == 2
            assert client._client is None
            assert client._api_client is None

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_config):
        """Test async context manager."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client

            async with AygaParserHttpClient(config=mock_config) as client:
                assert client._client is not None
                assert client._api_client is not None

            assert mock_client.aclose.call_count == 2

    @pytest.mark.asyncio
    async def test_ensure_connected_not_connected(self, mock_config):
        """Test _ensure_connected raises error when not connected."""
        client = AygaParserHttpClient(config=mock_config)
        with pytest.raises(AygaParserHTTPError) as exc_info:
            client._ensure_connected()
        assert "Client not connected" in str(exc_info.value)


class TestAygaParserHttpClientRequests:
    """Test suite for HTTP client requests."""

    @pytest.fixture
    async def connected_client(self, mock_config, mock_httpx_client):
        """Create a connected client fixture."""
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            yield client
            await client.close()

    @pytest.mark.asyncio
    async def test_ping_success(self, mock_config, mock_httpx_client):
        """Test successful ping."""
        mock_httpx_client.post.return_value.json.return_value = {"success": 1, "data": "pong"}
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.ping()
            
            assert result == True  # API returns 1, not Python True
            mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_ping_failure(self, mock_config, mock_httpx_client):
        """Test ping with API error."""
        mock_httpx_client.post.return_value.json.return_value = {"success": 0, "error": "Auth failed"}
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            
            with pytest.raises(AygaParserAPIError):
                await client.ping()

    @pytest.mark.asyncio
    async def test_one_request_success(self, mock_config, mock_httpx_client):
        """Test oneRequest method."""
        mock_httpx_client.post.return_value.json.return_value = {
            "success": 1,
            "data": {"results": ["test"]},
        }
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AygaParserHttpClient(config=mock_config)
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
        client = AygaParserHttpClient(config=mock_config)
        
        with pytest.raises(AygaParserValidationError) as exc_info:
            await client.one_request(parser="", query="test")
        assert "Parser name is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_one_request_validation_empty_query(self, mock_config):
        """Test oneRequest with empty query."""
        client = AygaParserHttpClient(config=mock_config)
        
        with pytest.raises(AygaParserValidationError) as exc_info:
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
            client = AygaParserHttpClient(config=mock_config)
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
            client = AygaParserHttpClient(config=mock_config)
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
            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_parser_info("SE::Google")
            
            assert result["name"] == "SE::Google"

    @pytest.mark.asyncio
    async def test_get_parser_info_validation(self, mock_config):
        """Test getParserInfo with empty parser name."""
        client = AygaParserHttpClient(config=mock_config)
        
        with pytest.raises(AygaParserValidationError) as exc_info:
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
            client = AygaParserHttpClient(config=mock_config)
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
            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_task_info("task1")
            
            assert result["id"] == "task1"
            assert result["progress"] == 50

    @pytest.mark.asyncio
    async def test_cancel_task(self, mock_config, mock_httpx_client):
        """Test cancelTask method."""
        mock_httpx_client.post.return_value.json.return_value = {"success": 1}
        
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = AygaParserHttpClient(config=mock_config)
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
            client = AygaParserHttpClient(config=mock_config)
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
            client = AygaParserHttpClient(config=mock_config)
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
            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_results("task1")
            
            assert "results" in result


class TestAygaParserHttpClientErrors:
    """Test suite for HTTP client error handling."""

    @pytest.mark.asyncio
    async def test_timeout_error(self, mock_config):
        """Test timeout error handling."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Connection timeout")
            MockClient.return_value = mock_client
            
            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            
            with pytest.raises(AygaParserTimeoutError) as exc_info:
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
            
            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            
            with pytest.raises(AygaParserHTTPError) as exc_info:
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
            
            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            
            with pytest.raises(AygaParserHTTPError) as exc_info:
                await client.ping()
            assert "Invalid JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_auth_error_no_password(self, mock_config):
        """Test authentication error when password not configured."""
        mock_config.get_password.return_value = None

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()

            with pytest.raises(AygaParserAuthError) as exc_info:
                await client.ping()
            assert "password not configured" in str(exc_info.value)


class TestAygaParserHttpClientRedisWrapperApi:
    """Test suite for the Redis Wrapper REST API methods (list_parsers, submit_task, etc)."""

    def _mock_api_response(self, json_data, status_code=200):
        response = MagicMock()
        response.json.return_value = json_data
        response.status_code = status_code
        response.text = json.dumps(json_data)

        def _raise_for_status():
            if status_code >= 400:
                request = MagicMock()
                raise httpx.HTTPStatusError(
                    f"HTTP {status_code}", request=request, response=response
                )

        response.raise_for_status = MagicMock(side_effect=_raise_for_status)
        return response

    @pytest.mark.asyncio
    async def test_connect_sets_api_client_with_api_key_header(self, mock_config):
        """Test that connect() configures a second client for api_url with X-API-Key."""
        mock_config.api_url = "https://redis.ayga.tech"
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()

            assert client._api_client is not None
            # Two AsyncClient instances should have been created: http_url + api_url
            assert MockClient.call_count == 2
            api_call_kwargs = MockClient.call_args_list[1].kwargs
            assert api_call_kwargs["base_url"] == "https://redis.ayga.tech"
            assert api_call_kwargs["headers"]["X-API-Key"] == "test_password"

    @pytest.mark.asyncio
    async def test_list_parsers(self, mock_config):
        payload = {
            "parsers": [
                {
                    "id": "perplexity",
                    "name": "Perplexity AI",
                    "aparser_name": "FreeAI::Perplexity",
                    "category": "FreeAI",
                }
            ],
            "count": 1,
        }
        mock_response = self._mock_api_response(payload)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.list_parsers(category="FreeAI")

            assert result["count"] == 1
            assert result["parsers"][0]["id"] == "perplexity"
            mock_client.request.assert_called_once()
            call_args = mock_client.request.call_args
            assert call_args.args[0] == "GET"
            assert call_args.args[1] == "/parsers"
            assert call_args.kwargs["params"] == {"category": "FreeAI"}

    @pytest.mark.asyncio
    async def test_get_parser(self, mock_config):
        payload = {"id": "perplexity", "aparser_name": "FreeAI::Perplexity"}
        mock_response = self._mock_api_response(payload)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_parser("perplexity")

            assert result["id"] == "perplexity"

    @pytest.mark.asyncio
    async def test_get_parser_validation_empty_id(self, mock_config):
        client = AygaParserHttpClient(config=mock_config)
        with pytest.raises(AygaParserValidationError):
            await client.get_parser("")

    @pytest.mark.asyncio
    async def test_get_parser_presets(self, mock_config):
        payload = {"presets": [{"name": "default"}]}
        mock_response = self._mock_api_response(payload)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_parser_presets("perplexity")

            assert "presets" in result

    @pytest.mark.asyncio
    async def test_validate_parser(self, mock_config):
        payload = {"is_valid": True, "error": None}
        mock_response = self._mock_api_response(payload)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.validate_parser("perplexity", query="test")

            assert result["is_valid"] is True

    @pytest.mark.asyncio
    async def test_list_categories(self, mock_config):
        payload = {"categories": ["FreeAI", "SE"]}
        mock_response = self._mock_api_response(payload)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.list_categories()

            assert "categories" in result

    @pytest.mark.asyncio
    async def test_submit_task_success(self, mock_config):
        payload = {
            "task_id": "task_123",
            "status": "submitted",
            "parser": "FreeAI::Perplexity",
            "submitted_at": "2026-01-01T00:00:00Z",
            "queue_position": 1,
        }
        mock_response = self._mock_api_response(payload)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.submit_task(parser="FreeAI::Perplexity", query="hello")

            assert result["task_id"] == "task_123"
            call_args = mock_client.request.call_args
            assert call_args.args[0] == "POST"
            assert call_args.args[1] == "/parsers/tasks"
            assert call_args.kwargs["json"]["parser"] == "FreeAI::Perplexity"
            assert call_args.kwargs["json"]["query"] == "hello"

    @pytest.mark.asyncio
    async def test_submit_task_validation_empty_parser(self, mock_config):
        client = AygaParserHttpClient(config=mock_config)
        with pytest.raises(AygaParserValidationError):
            await client.submit_task(parser="", query="hello")

    @pytest.mark.asyncio
    async def test_submit_task_validation_empty_query(self, mock_config):
        client = AygaParserHttpClient(config=mock_config)
        with pytest.raises(AygaParserValidationError):
            await client.submit_task(parser="FreeAI::Perplexity", query="")

    @pytest.mark.asyncio
    async def test_submit_task_auth_required(self, mock_config):
        mock_config.get_password.return_value = None

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()

            with pytest.raises(AygaParserAuthError):
                await client.submit_task(parser="FreeAI::Perplexity", query="hello")

    @pytest.mark.asyncio
    async def test_get_task_status(self, mock_config):
        payload = {"task_id": "task_123", "ready": True, "checked_at": "2026-01-01T00:00:00Z"}
        mock_response = self._mock_api_response(payload)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_task_status("task_123")

            assert result["ready"] is True

    @pytest.mark.asyncio
    async def test_get_task_result_ready(self, mock_config):
        payload = {
            "task_id": "task_123",
            "status": "completed",
            "data": {"results": ["x"]},
            "format": "parsed",
            "wait_time_seconds": 2.5,
            "parser": "FreeAI::Perplexity",
        }
        mock_response = self._mock_api_response(payload)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_task_result("task_123")

            assert result["status"] == "completed"
            call_args = mock_client.request.call_args
            assert call_args.args[0] == "GET"
            assert call_args.args[1] == "/parsers/results/task_123"
            assert call_args.kwargs["params"] == {"format": "parsed"}

    @pytest.mark.asyncio
    async def test_get_task_result_not_ready_returns_none(self, mock_config):
        mock_response = self._mock_api_response({"detail": "Not ready"}, status_code=404)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()
            result = await client.get_task_result("task_123")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_task_result_server_error_raises(self, mock_config):
        mock_response = self._mock_api_response({"detail": "Server error"}, status_code=500)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()

            with pytest.raises(AygaParserHTTPError):
                await client.get_task_result("task_123")

    @pytest.mark.asyncio
    async def test_get_task_result_auth_required(self, mock_config):
        mock_config.get_password.return_value = None

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()

            with pytest.raises(AygaParserAuthError):
                await client.get_task_result("task_123")

    @pytest.mark.asyncio
    async def test_api_request_timeout(self, mock_config):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
            MockClient.return_value = mock_client

            client = AygaParserHttpClient(config=mock_config)
            await client.connect()

            with pytest.raises(AygaParserTimeoutError):
                await client.list_parsers()

    @pytest.mark.asyncio
    async def test_api_not_connected_raises(self, mock_config):
        client = AygaParserHttpClient(config=mock_config)
        with pytest.raises(AygaParserHTTPError):
            client._ensure_api_connected()
