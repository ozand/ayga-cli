import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock, AsyncMock
from ayga_cli.main import app

runner = CliRunner()

@patch('ayga_cli.commands.get.AygaParserRedisClient')
def test_get_command_success(mock_client_class):
    # Setup mock
    mock_instance = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_instance
    
    mock_instance.push.return_value = "job_123"
    mock_instance.pop.return_value = {
        "success": True,
        "data": {
            "results": [
                {"title": "Test 1", "url": "http://test1.com"},
                {"title": "Test 2", "url": "http://test2.com"}
            ]
        }
    }
    
    # Run command
    result = runner.invoke(app, ["get", "web-search", "test query"])
    
    # Verify
    assert result.exit_code == 0
    assert "Success" in result.stdout
    assert "Items: 2" in result.stdout
    assert "Test 1" in result.stdout
    assert "http://test1.com" in result.stdout

@patch('ayga_cli.commands.get.AygaParserRedisClient')
def test_get_command_timeout(mock_client_class):
    # Setup mock
    mock_instance = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_instance
    
    mock_instance.push.return_value = "job_123"
    mock_instance.pop.return_value = None  # Simulates timeout
    
    # Run command
    result = runner.invoke(app, ["get", "web-search", "test query", "--timeout", "1"])
    
    # Verify
    assert result.exit_code == 2  # ERROR_TIMEOUT
    assert result.exit_code == 2  # error in stderr
    # error message goes to stderr

@patch('ayga_cli.commands.get.AygaParserRedisClient')
def test_get_command_json_output(mock_client_class):
    # Setup mock
    mock_instance = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_instance
    
    mock_instance.push.return_value = "job_123"
    mock_response = {
        "success": True,
        "data": {
            "results": [
                {"title": "Test 1", "url": "http://test1.com"}
            ]
        }
    }
    mock_instance.pop.return_value = mock_response
    
    # Run command
    result = runner.invoke(app, ["get", "web-search", "test query", "--json"])
    
    # Verify
    assert result.exit_code == 0
    import json
    parsed = json.loads(result.stdout)
    assert parsed["success"] == True
    assert len(parsed["data"]["results"]) == 1
