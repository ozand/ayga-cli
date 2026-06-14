"""Shared fixtures for ayga-parser CLI tests."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_config():
    """Mock ayga-parserConfig for testing"""
    from ayga_cli.config import ayga-parserConfig
    from pydantic import SecretStr
    config = MagicMock(spec=ayga-parserConfig)
    config.http_url = "http://localhost:9091/API"
    config.redis_host = "localhost"
    config.redis_port = 6379
    config.redis_queue = "ayga-parser_redis_api"
    config.redis_result_queue = "ayga-parser_results"
    config.redis_db = 0
    config.redis_ssl = False
    config.redis_password = None
    # Create a proper mock for password that behaves like SecretStr
    password_mock = MagicMock(spec=SecretStr)
    password_mock.get_secret_value.return_value = "test_password"
    config.password = password_mock
    config.default_timeout = 300
    config.default_preset = "default"
    config.default_config_preset = "default"
    config.log_level = "INFO"
    config.get_password.return_value = "test_password"
    config.get_http_basic_auth.return_value = ("", "test_password")
    return config


@pytest.fixture(autouse=True)
def clear_ayga-parser_env(monkeypatch):
    """Clear ayga-parser environment variables for test isolation."""
    for key in list(__import__("os").environ):
        if key.startswith("ayga-parser_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def isolate_config_dir(monkeypatch, tmp_path):
    """Redirect config file loading to an isolated temp directory."""
    monkeypatch.setattr("ayga_cli.config.CONFIG_DIR", tmp_path / "ayga-cli")


@pytest.fixture
def mock_redis():
    """Mock Redis connection"""
    redis = AsyncMock()
    redis.lpush = AsyncMock(return_value=1)
    redis.blpop = AsyncMock(return_value=("queue", '{"success": 1}'))
    redis.llen = AsyncMock(return_value=0)
    redis.ping = AsyncMock(return_value=True)
    redis.close = AsyncMock()
    redis.aclose = AsyncMock()
    return redis


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient"""
    client = AsyncMock()
    response = MagicMock()
    response.json.return_value = {"success": 1, "data": "test"}
    response.raise_for_status = MagicMock()
    response.status_code = 200
    response.text = '{"success": 1, "data": "test"}'
    client.post = AsyncMock(return_value=response)
    return client


@pytest.fixture
def mock_httpx_response():
    """Mock httpx.Response"""
    response = MagicMock()
    response.json.return_value = {"success": 1, "data": "test"}
    response.raise_for_status = MagicMock()
    response.status_code = 200
    response.text = '{"success": 1, "data": "test"}'
    return response
