"""Tests for +extract and +research helpers."""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, AsyncMock

from ayga_cli.main import app

runner = CliRunner()


# --- +extract ---

@patch("ayga_cli.commands.helpers.extract.AygaParserRedisClient")
def test_extract_calls_article_source(mock_cls):
    inst = AsyncMock()
    inst.push.return_value = "job_ext_1"
    inst.pop.return_value = {
        "title": "Test Article",
        "content": "<p>Hello world</p>",
        "url": "https://example.com",
    }
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["+extract", "extract", "https://example.com"])
    assert result.exit_code == 0
    inst.push.assert_called_once_with(source="article", query="https://example.com")


@patch("ayga_cli.commands.helpers.extract.AygaParserRedisClient")
def test_extract_timeout(mock_cls):
    inst = AsyncMock()
    inst.push.return_value = "job_x"
    inst.pop.return_value = None
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["+extract", "extract", "https://example.com"])
    assert result.exit_code == 2  # ERROR_TIMEOUT


# --- +research ---

@patch("ayga_cli.commands.helpers.research.AygaParserRedisClient")
def test_research_calls_both_sources(mock_cls):
    inst = AsyncMock()
    # push returns different job ids
    inst.push.side_effect = ["job_web", "job_ai"]
    inst.pop.side_effect = [
        {"results": [{"title": "Web result", "url": "http://x.com", "snippet": "x"}]},
        {"answer": "AI answer text"},
    ]
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["+research", "research", "test query"])
    assert result.exit_code == 0
    calls = [c.kwargs.get("source") or c.args[0] if c.args else c.kwargs.get("source")
             for c in inst.push.call_args_list]
    sources_used = [c.kwargs.get("source") for c in inst.push.call_args_list]
    assert "web-search" in sources_used
    assert "ai-answer" in sources_used


@patch("ayga_cli.commands.helpers.research.AygaParserRedisClient")
def test_research_json_output(mock_cls):
    inst = AsyncMock()
    inst.push.side_effect = ["j1", "j2"]
    inst.pop.side_effect = [{"results": []}, {"answer": "42"}]
    mock_cls.return_value.__aenter__.return_value = inst
    result = runner.invoke(app, ["+research", "research", "q", "--json"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.stdout)
    assert "query" in data
    assert "web_search" in data
    assert "ai_answer" in data
