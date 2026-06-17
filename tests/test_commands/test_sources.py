"""Tests for sources commands."""

import json
import pytest
from typer.testing import CliRunner
from unittest.mock import patch, AsyncMock

from ayga_cli.main import app

runner = CliRunner()

SOURCES = [
    {"name": "web-search", "category": "search", "description": "Web search engine"},
    {"name": "ai-answer", "category": "ai", "description": "AI answer generation"},
]


@pytest.fixture(autouse=True)
def no_cache(monkeypatch):
    """Disable cache for all tests — always fetch from server."""
    monkeypatch.setattr("ayga_cli.commands.sources.load_cache", lambda: None)
    monkeypatch.setattr("ayga_cli.commands.sources.save_cache", lambda x: None)


@patch("ayga_cli.commands.sources.AygaParserRedisClient")
def test_sources_list_success(mock_cls):
    inst = AsyncMock()
    mock_cls.return_value.__aenter__.return_value = inst
    inst.get_sources.return_value = SOURCES
    result = runner.invoke(app, ["sources", "list", "--no-cache"])
    assert result.exit_code == 0
    assert "web-search" in result.stdout
    assert "ai-answer" in result.stdout


@patch("ayga_cli.commands.sources.AygaParserRedisClient")
def test_sources_list_empty(mock_cls):
    inst = AsyncMock()
    mock_cls.return_value.__aenter__.return_value = inst
    inst.get_sources.return_value = []
    result = runner.invoke(app, ["sources", "list", "--no-cache"])
    assert result.exit_code == 0
    assert "No sources" in result.stdout


@patch("ayga_cli.commands.sources.AygaParserRedisClient")
def test_sources_list_json(mock_cls):
    inst = AsyncMock()
    mock_cls.return_value.__aenter__.return_value = inst
    inst.get_sources.return_value = SOURCES
    result = runner.invoke(app, ["sources", "list", "--json", "--no-cache"])
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert "sources" in parsed
    assert len(parsed["sources"]) == 2


@patch("ayga_cli.commands.sources.AygaParserRedisClient")
def test_sources_info_found(mock_cls):
    inst = AsyncMock()
    mock_cls.return_value.__aenter__.return_value = inst
    inst.get_sources.return_value = SOURCES
    result = runner.invoke(app, ["sources", "info", "web-search"])
    assert result.exit_code == 0
    assert "web-search" in result.stdout


@patch("ayga_cli.commands.sources.AygaParserRedisClient")
def test_sources_info_not_found(mock_cls):
    from ayga_cli.exceptions import exit_codes
    inst = AsyncMock()
    mock_cls.return_value.__aenter__.return_value = inst
    inst.get_sources.return_value = SOURCES
    result = runner.invoke(app, ["sources", "info", "nonexistent"])
    assert result.exit_code == exit_codes.ERROR_NOT_FOUND
