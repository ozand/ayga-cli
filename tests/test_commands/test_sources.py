import pytest
from typer.testing import CliRunner
from unittest.mock import patch, AsyncMock
from ayga_cli.main import app

runner = CliRunner()

@patch('ayga_cli.commands.sources.AygaParserRedisClient')
def test_sources_list_success(mock_client_class):
    # Setup mock
    mock_instance = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_instance
    
    mock_instance.get_sources.return_value = [
        {"name": "web-search", "category": "search", "description": "Web search engine"},
        {"name": "ai-answer", "category": "ai", "description": "AI answer generation"}
    ]
    
    # Run command
    result = runner.invoke(app, ["sources", "list"])
    
    # Verify
    assert result.exit_code == 0
    assert "Available Sources" in result.stdout
    assert "web-search" in result.stdout
    assert "search" in result.stdout
    assert "ai-answer" in result.stdout

@patch('ayga_cli.commands.sources.AygaParserRedisClient')
def test_sources_list_empty(mock_client_class):
    # Setup mock
    mock_instance = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_instance
    
    mock_instance.get_sources.return_value = []
    
    # Run command
    result = runner.invoke(app, ["sources", "list"])
    
    # Verify
    assert result.exit_code == 0
    assert "No sources configured on server" in result.stdout

@patch('ayga_cli.commands.sources.AygaParserRedisClient')
def test_sources_list_json(mock_client_class):
    # Setup mock
    mock_instance = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_instance
    
    mock_instance.get_sources.return_value = [
        {"name": "web-search", "category": "search", "description": "Web search engine"}
    ]
    
    # Run command
    result = runner.invoke(app, ["sources", "list", "--json"])
    
    # Verify
    assert result.exit_code == 0
    import json
    parsed = json.loads(result.stdout)
    assert "sources" in parsed
    assert len(parsed["sources"]) == 1
    assert parsed["sources"][0]["name"] == "web-search"
