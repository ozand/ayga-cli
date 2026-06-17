"""Tests for --fields, --stream, --dry-run flags and exit codes."""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, AsyncMock

from ayga_cli.main import app
from ayga_cli.exceptions import exit_codes

runner = CliRunner()

MOCK_RESULT = {
    "success": True,
    "results": [
        {"title": "Result 1", "url": "http://r1.com", "snippet": "Snippet 1"},
        {"title": "Result 2", "url": "http://r2.com", "snippet": "Snippet 2"},
    ],
}


def _make_mock(result=MOCK_RESULT, job_id="job_123"):
    mock = AsyncMock()
    mock.push.return_value = job_id
    mock.pop.return_value = result
    return mock


# --- --fields ---

@patch("ayga_cli.commands.get.AygaParserRedisClient")
def test_fields_filters_output(mock_cls):
    inst = _make_mock({"results": [
        {"title": "T1", "url": "U1", "snippet": "S1"},
        {"title": "T2", "url": "U2", "snippet": "S2"},
    ]})
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["get", "web-search", "query", "--stream", "--fields", "title,url"])
    assert result.exit_code == 0
    import json
    lines = [l for l in result.stdout.strip().splitlines() if l]
    assert len(lines) == 2
    for line in lines:
        obj = json.loads(line)
        assert "title" in obj
        assert "snippet" not in obj


@patch("ayga_cli.commands.get.AygaParserRedisClient")
def test_fields_missing_field_no_crash(mock_cls):
    inst = _make_mock({"title": "T", "url": "U"})
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["get", "web-search", "q", "--json", "--fields", "title,nonexistent"])
    assert result.exit_code == 0


# --- --stream ---

@patch("ayga_cli.commands.get.AygaParserRedisClient")
def test_stream_ndjson_output(mock_cls):
    inst = _make_mock()
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["get", "web-search", "query", "--stream"])
    assert result.exit_code == 0
    import json
    lines = [l for l in result.stdout.strip().splitlines() if l]
    assert len(lines) == 2
    for line in lines:
        obj = json.loads(line)
        assert "title" in obj


@patch("ayga_cli.commands.get.AygaParserRedisClient")
def test_stream_with_fields(mock_cls):
    inst = _make_mock({"results": [
        {"title": "T1", "url": "U1", "snippet": "S1"},
        {"title": "T2", "url": "U2", "snippet": "S2"},
    ]})
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["get", "web-search", "q", "--stream", "--fields", "title"])
    assert result.exit_code == 0
    import json
    lines = [l for l in result.stdout.strip().splitlines() if l]
    for line in lines:
        obj = json.loads(line)
        assert "title" in obj
        assert "url" not in obj
        assert "snippet" not in obj


# --- --dry-run ---

def test_dry_run_no_server_call():
    with patch("ayga_cli.commands.get.AygaParserRedisClient") as mock_cls:
        result = runner.invoke(app, ["get", "web-search", "test", "--dry-run"])
        assert result.exit_code == 0
        mock_cls.return_value.__aenter__.assert_not_called()
        assert "DRY RUN" in result.stdout or "dry_run" in result.stdout


def test_dry_run_json():
    result = runner.invoke(app, ["get", "web-search", "test", "--dry-run", "--json"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.stdout)
    assert data["dry_run"] is True
    assert "payload" in data
    assert "result_queue" in data


# --- exit codes ---

@patch("ayga_cli.commands.get.AygaParserRedisClient")
def test_exit_code_timeout(mock_cls):
    inst = AsyncMock()
    inst.push.return_value = "job_x"
    inst.pop.return_value = None  # timeout
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["get", "web-search", "q"])
    assert result.exit_code == exit_codes.ERROR_TIMEOUT


@patch("ayga_cli.commands.get.AygaParserRedisClient")
def test_exit_code_unavailable(mock_cls):
    mock_cls.return_value.__aenter__.side_effect = ConnectionError("refused")
    result = runner.invoke(app, ["get", "web-search", "q"])
    assert result.exit_code == exit_codes.ERROR_UNAVAILABLE


def test_exit_code_empty_source():
    result = runner.invoke(app, ["get", "", "query"])
    assert result.exit_code == exit_codes.ERROR_INPUT


def test_exit_code_empty_query():
    result = runner.invoke(app, ["get", "web-search", ""])
    assert result.exit_code == exit_codes.ERROR_INPUT
