# redis command removed from public API (architecture decision)
import pytest
pytestmark = pytest.mark.skip(reason="redis subcommand removed from public CLI — use ayga_parser get instead")

"""Tests for redis command."""

import pytest
from typer.testing import CliRunner
from unittest.mock import AsyncMock, patch, MagicMock

from ayga_cli.main import app

runner = CliRunner()


class TestRedisPushCommand:
    """Test suite for redis push command."""

    def test_redis_push_help(self):
        """Test redis push command help."""
        result = runner.invoke(app, ["redis", "push", "--help"])
        assert result.exit_code == 0
        assert "Push a task to Redis queue" in result.output

    @patch("ayga_cli.commands.redis.AygaParserRedisClient")
    def test_redis_push_with_args(self, mock_client_cls):
        """Test redis push with required arguments."""
        mock_client = AsyncMock()
        mock_client.push.return_value = "test_result_queue"
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        result = runner.invoke(app, ["redis", "push", "SE::Google", "test query"])
        assert result.exit_code == 0
        assert "Queued" in result.output or "completed" in result.output.lower() or "Queued" in result.output

    @patch("ayga_cli.commands.redis.AygaParserRedisClient")
    def test_redis_push_with_queue(self, mock_client_cls):
        """Test redis push with custom queue."""
        mock_client = AsyncMock()
        mock_client.push.return_value = "custom_queue"
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        result = runner.invoke(app, [
            "redis", "push",
            "SE::Google", "test",
            "--result-queue", "custom_queue"
        ])
        assert result.exit_code == 0
        assert "custom_queue" in result.output

    @patch("ayga_cli.commands.redis.AygaParserRedisClient")
    def test_redis_push_json_output(self, mock_client_cls):
        """Test redis push with JSON output."""
        mock_client = AsyncMock()
        mock_client.push.return_value = "test_result_queue"
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        result = runner.invoke(app, [
            "redis", "push",
            "SE::Google", "test",
            "--json"
        ])
        assert result.exit_code == 0
        import json
        try:
            data = json.loads(result.output)
            assert data.get("status") == "queued"
        except json.JSONDecodeError:
            pass

    def test_redis_push_missing_args(self):
        """Test redis push without required arguments."""
        result = runner.invoke(app, ["redis", "push"])
        assert result.exit_code != 0

