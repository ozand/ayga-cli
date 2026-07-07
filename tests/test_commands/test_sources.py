"""Tests for sources commands."""

import json

import pytest
from typer.testing import CliRunner
from unittest.mock import AsyncMock, patch

from ayga_cli.main import app

runner = CliRunner()

PARSERS_RESPONSE = {
    "parsers": [
        {
            "id": "perplexity",
            "name": "Perplexity AI",
            "category": "FreeAI",
            "description": "Research with Perplexity AI",
            "tags": ["research"],
            "aparser_name": "FreeAI::Perplexity",
            "capabilities": {},
        },
        {
            "id": "google_search",
            "name": "Google Search",
            "category": "SE",
            "description": "Search Google",
            "tags": ["search"],
            "aparser_name": "SE::Google",
            "capabilities": {},
        },
    ],
    "count": 2,
}


@pytest.fixture(autouse=True)
def no_cache(monkeypatch):
    """Disable cache for all tests — always fetch from server."""
    monkeypatch.setattr("ayga_cli.commands.sources.load_cache", lambda: None)
    monkeypatch.setattr("ayga_cli.commands.sources.save_cache", lambda x: None)


def _mock_http_client(list_parsers_return=PARSERS_RESPONSE, get_parser_return=None):
    inst = AsyncMock()
    inst.list_parsers.return_value = list_parsers_return
    if get_parser_return is not None:
        inst.get_parser.return_value = get_parser_return
    return inst


@patch("ayga_cli.commands.sources.AygaParserHttpClient")
def test_sources_list_success(mock_cls):
    inst = _mock_http_client()
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["sources", "list", "--no-cache"])
    assert result.exit_code == 0
    assert "perplexity" in result.stdout
    assert "google_search" in result.stdout


@patch("ayga_cli.commands.sources.AygaParserHttpClient")
def test_sources_list_empty(mock_cls):
    inst = _mock_http_client(list_parsers_return={"parsers": [], "count": 0})
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["sources", "list", "--no-cache"])
    assert result.exit_code == 0
    assert "No sources" in result.stdout


@patch("ayga_cli.commands.sources.AygaParserHttpClient")
def test_sources_list_json(mock_cls):
    inst = _mock_http_client()
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["sources", "list", "--json", "--no-cache"])
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert "sources" in parsed
    assert len(parsed["sources"]) == 2
    assert parsed["sources"][0]["id"] == "perplexity"
    assert parsed["sources"][0]["aparser_name"] == "FreeAI::Perplexity"


@patch("ayga_cli.commands.sources.AygaParserHttpClient")
def test_sources_info_found(mock_cls):
    inst = _mock_http_client()
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["sources", "info", "perplexity"])
    assert result.exit_code == 0
    assert "perplexity" in result.stdout


@patch("ayga_cli.commands.sources.AygaParserHttpClient")
def test_sources_info_not_found(mock_cls):
    from ayga_cli.exceptions import exit_codes

    inst = _mock_http_client()
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["sources", "info", "nonexistent"])
    assert result.exit_code == exit_codes.ERROR_NOT_FOUND


@patch("ayga_cli.commands.sources.AygaParserHttpClient")
def test_sources_list_server_unavailable(mock_cls):
    from ayga_cli.exceptions import exit_codes

    mock_cls.return_value.__aenter__.side_effect = ConnectionError("refused")
    result = runner.invoke(app, ["sources", "list", "--no-cache"])
    assert result.exit_code == exit_codes.ERROR_UNAVAILABLE
