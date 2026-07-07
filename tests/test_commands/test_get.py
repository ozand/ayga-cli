import pytest
from typer.testing import CliRunner
from unittest.mock import patch, AsyncMock

from ayga_cli.main import app

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


@pytest.fixture(autouse=True)
def cached_sources(monkeypatch):
    """Pre-populate the sources cache so _resolve_aparser_name hits it directly."""
    monkeypatch.setattr("ayga_cli.commands.get.load_cache", lambda: SOURCE_CACHE)
    monkeypatch.setattr("ayga_cli.commands.get.save_cache", lambda x: None)


def _make_client(submit_return=None, result_return=None):
    inst = AsyncMock()
    inst.submit_task.return_value = submit_return or {
        "task_id": "task_123",
        "status": "submitted",
        "parser": "FreeAI::Perplexity",
        "submitted_at": "2026-01-01T00:00:00Z",
        "queue_position": 1,
    }
    inst.get_task_result.return_value = result_return
    return inst


@patch("ayga_cli.commands.get.AygaParserHttpClient")
def test_get_command_success(mock_client_class):
    inst = _make_client(
        result_return={
            "task_id": "task_123",
            "status": "completed",
            "data": {
                "results": [
                    {"title": "Test 1", "url": "http://test1.com"},
                    {"title": "Test 2", "url": "http://test2.com"},
                ]
            },
            "format": "parsed",
        }
    )
    mock_client_class.return_value.__aenter__.return_value = inst

    result = runner.invoke(app, ["get", "perplexity", "test query"])

    assert result.exit_code == 0
    assert "Success" in result.stdout
    assert "Items: 2" in result.stdout
    assert "Test 1" in result.stdout
    assert "http://test1.com" in result.stdout
    inst.submit_task.assert_called_once()
    assert inst.submit_task.call_args.kwargs["parser"] == "FreeAI::Perplexity"


@patch("ayga_cli.commands.get.AygaParserHttpClient")
def test_get_command_timeout(mock_client_class):
    inst = _make_client(result_return=None)  # never ready -> timeout
    mock_client_class.return_value.__aenter__.return_value = inst

    result = runner.invoke(app, ["get", "perplexity", "test query", "--timeout", "1"])

    assert result.exit_code == 2  # ERROR_TIMEOUT


@patch("ayga_cli.commands.get.AygaParserHttpClient")
def test_get_command_json_output(mock_client_class):
    mock_response = {
        "task_id": "task_123",
        "status": "completed",
        "data": {"results": [{"title": "Test 1", "url": "http://test1.com"}]},
        "format": "parsed",
    }
    inst = _make_client(result_return=mock_response)
    mock_client_class.return_value.__aenter__.return_value = inst

    result = runner.invoke(app, ["get", "perplexity", "test query", "--json"])

    assert result.exit_code == 0
    import json

    parsed = json.loads(result.stdout)
    assert parsed["status"] == "completed"
    assert len(parsed["data"]["results"]) == 1


@patch("ayga_cli.commands.get.AygaParserHttpClient")
def test_get_command_source_not_found(mock_client_class):
    """Source not in cache and not returned by a fresh fetch -> ERROR_NOT_FOUND."""
    inst = _make_client()
    inst.list_parsers.return_value = {"parsers": [], "count": 0}
    mock_client_class.return_value.__aenter__.return_value = inst

    result = runner.invoke(app, ["get", "unknown_source", "test query"])

    from ayga_cli.exceptions import exit_codes

    assert result.exit_code == exit_codes.ERROR_NOT_FOUND


@patch("ayga_cli.commands.get.asyncio.sleep", new_callable=AsyncMock)
@patch("ayga_cli.commands.get.AygaParserHttpClient")
def test_get_command_retries_submit_on_503(mock_client_class, _mock_sleep):
    """A busy backend rejects the first submit with 503; get should retry and succeed."""
    from ayga_cli.exceptions import AygaParserHTTPError

    inst = _make_client(
        result_return={
            "task_id": "task_123",
            "status": "completed",
            "data": {"results": [{"title": "Test 1", "url": "http://test1.com"}]},
            "format": "parsed",
        }
    )
    inst.submit_task.side_effect = [
        AygaParserHTTPError(message="busy", status_code=503),
        {
            "task_id": "task_123",
            "status": "submitted",
            "parser": "FreeAI::Perplexity",
            "submitted_at": "2026-01-01T00:00:00Z",
            "queue_position": 1,
        },
    ]
    mock_client_class.return_value.__aenter__.return_value = inst

    result = runner.invoke(app, ["get", "perplexity", "test query", "--timeout", "30"])

    assert result.exit_code == 0
    assert "Success" in result.stdout
    assert inst.submit_task.call_count == 2  # first 503, then accepted


@patch("ayga_cli.commands.get.asyncio.sleep", new_callable=AsyncMock)
@patch("ayga_cli.commands.get.AygaParserHttpClient")
def test_get_command_persistent_503_times_out(mock_client_class, _mock_sleep):
    """Submit rejected with 503 for the whole budget -> ERROR_TIMEOUT, not a crash."""
    from ayga_cli.exceptions import AygaParserHTTPError, exit_codes

    inst = _make_client()
    inst.submit_task.side_effect = AygaParserHTTPError(message="busy", status_code=503)
    mock_client_class.return_value.__aenter__.return_value = inst

    result = runner.invoke(app, ["get", "perplexity", "test query", "--timeout", "1"])

    assert result.exit_code == exit_codes.ERROR_TIMEOUT
    assert inst.get_task_result.call_count == 0  # never got past submit


@patch("ayga_cli.commands.get.AygaParserHttpClient")
def test_get_command_non_503_error_fails_fast(mock_client_class):
    """A non-503 HTTP error must propagate immediately, not retry."""
    from ayga_cli.exceptions import AygaParserHTTPError, exit_codes

    inst = _make_client()
    inst.submit_task.side_effect = AygaParserHTTPError(message="boom", status_code=500)
    mock_client_class.return_value.__aenter__.return_value = inst

    result = runner.invoke(app, ["get", "perplexity", "test query", "--timeout", "30"])

    assert result.exit_code == exit_codes.ERROR_UNAVAILABLE
    assert inst.submit_task.call_count == 1  # no retry on non-503
