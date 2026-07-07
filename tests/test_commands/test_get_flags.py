"""Tests for --fields, --stream, --dry-run flags and exit codes."""

import json

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, AsyncMock

from ayga_cli.main import app
from ayga_cli.exceptions import exit_codes

runner = CliRunner()

SOURCE_CACHE = [
    {
        "id": "perplexity",
        "name": "Perplexity AI",
        "aparser_name": "FreeAI::Perplexity",
        "category": "FreeAI",
        "description": "Research with Perplexity AI",
    }
]

MOCK_RESULT = {
    "task_id": "job_123",
    "status": "completed",
    "format": "parsed",
    "data": {
        "results": [
            {"title": "Result 1", "url": "http://r1.com", "snippet": "Snippet 1"},
            {"title": "Result 2", "url": "http://r2.com", "snippet": "Snippet 2"},
        ],
    },
}


@pytest.fixture(autouse=True)
def cached_sources(monkeypatch):
    """Pre-populate the sources cache so source resolution hits it directly."""
    monkeypatch.setattr("ayga_cli.commands.get.load_cache", lambda: SOURCE_CACHE)
    monkeypatch.setattr("ayga_cli.commands.get.save_cache", lambda x: None)


def _make_mock(result=None, task_id="job_123"):
    mock = AsyncMock()
    mock.submit_task.return_value = {
        "task_id": task_id,
        "status": "submitted",
        "parser": "FreeAI::Perplexity",
        "submitted_at": "2026-01-01T00:00:00Z",
        "queue_position": 1,
    }
    mock.get_task_result.return_value = MOCK_RESULT if result is None else result
    return mock


# --- --fields ---

@patch("ayga_cli.commands.get.AygaParserHttpClient")
def test_fields_filters_output(mock_cls):
    result_payload = {
        "data": {
            "results": [
                {"title": "T1", "url": "U1", "snippet": "S1"},
                {"title": "T2", "url": "U2", "snippet": "S2"},
            ]
        }
    }
    inst = _make_mock(result_payload)
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["get", "perplexity", "query", "--stream", "--fields", "title,url"])
    assert result.exit_code == 0
    lines = [line for line in result.stdout.strip().splitlines() if line]
    assert len(lines) == 2
    for line in lines:
        obj = json.loads(line)
        assert "title" in obj
        assert "snippet" not in obj


@patch("ayga_cli.commands.get.AygaParserHttpClient")
def test_fields_missing_field_no_crash(mock_cls):
    inst = _make_mock({"title": "T", "url": "U"})
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["get", "perplexity", "q", "--json", "--fields", "title,nonexistent"])
    assert result.exit_code == 0


# --- --stream ---

@patch("ayga_cli.commands.get.AygaParserHttpClient")
def test_stream_ndjson_output(mock_cls):
    inst = _make_mock()
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["get", "perplexity", "query", "--stream"])
    assert result.exit_code == 0
    lines = [line for line in result.stdout.strip().splitlines() if line]
    assert len(lines) == 2
    for line in lines:
        obj = json.loads(line)
        assert "title" in obj


@patch("ayga_cli.commands.get.AygaParserHttpClient")
def test_stream_with_fields(mock_cls):
    result_payload = {
        "data": {
            "results": [
                {"title": "T1", "url": "U1", "snippet": "S1"},
                {"title": "T2", "url": "U2", "snippet": "S2"},
            ]
        }
    }
    inst = _make_mock(result_payload)
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["get", "perplexity", "q", "--stream", "--fields", "title"])
    assert result.exit_code == 0
    lines = [line for line in result.stdout.strip().splitlines() if line]
    for line in lines:
        obj = json.loads(line)
        assert "title" in obj
        assert "url" not in obj
        assert "snippet" not in obj


# --- --dry-run ---

def test_dry_run_no_server_call():
    with patch("ayga_cli.commands.get.AygaParserHttpClient") as mock_cls:
        result = runner.invoke(app, ["get", "perplexity", "test", "--dry-run"])
        assert result.exit_code == 0
        mock_cls.return_value.__aenter__.assert_not_called()
        assert "DRY RUN" in result.stdout or "dry_run" in result.stdout


def test_dry_run_json():
    result = runner.invoke(app, ["get", "perplexity", "test", "--dry-run", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["dry_run"] is True
    assert "payload" in data
    assert "url" in data
    assert data["url"].endswith("/parsers/tasks")


# --- exit codes ---

@patch("ayga_cli.commands.get.AygaParserHttpClient")
def test_exit_code_timeout(mock_cls):
    inst = _make_mock(result=None)
    inst.get_task_result.return_value = None  # never ready
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["get", "perplexity", "q", "--timeout", "1"])
    assert result.exit_code == exit_codes.ERROR_TIMEOUT


@patch("ayga_cli.commands.get.AygaParserHttpClient")
def test_exit_code_unavailable(mock_cls):
    mock_cls.return_value.__aenter__.side_effect = ConnectionError("refused")
    result = runner.invoke(app, ["get", "perplexity", "q"])
    assert result.exit_code == exit_codes.ERROR_UNAVAILABLE


def test_exit_code_empty_source():
    result = runner.invoke(app, ["get", "", "query"])
    assert result.exit_code == exit_codes.ERROR_INPUT


def test_exit_code_empty_query():
    result = runner.invoke(app, ["get", "perplexity", ""])
    assert result.exit_code == exit_codes.ERROR_INPUT
