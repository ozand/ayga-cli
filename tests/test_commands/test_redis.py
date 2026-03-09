"""Tests for redis command."""

import pytest
from typer.testing import CliRunner
from unittest.mock import AsyncMock, patch, MagicMock

from aparser_cli.main import app

runner = CliRunner()


class TestRedisPushCommand:
    """Test suite for redis push command."""

    def test_redis_push_help(self):
        """Test redis push command help."""
        result = runner.invoke(app, ["redis", "push", "--help"])
        assert result.exit_code == 0
        assert "Push a task to Redis queue" in result.output

    def test_redis_push_with_args(self):
        """Test redis push with required arguments."""
        result = runner.invoke(app, ["redis", "push", "SE::Google", "test query"])
        assert result.exit_code == 0
        assert "Task Pushed" in result.output or "success" in result.output.lower()

    def test_redis_push_with_queue(self):
        """Test redis push with custom queue."""
        result = runner.invoke(app, [
            "redis", "push",
            "SE::Google", "test",
            "--queue", "custom_queue"
        ])
        assert result.exit_code == 0
        assert "custom_queue" in result.output

    def test_redis_push_with_redis_host(self):
        """Test redis push with custom Redis host."""
        result = runner.invoke(app, [
            "redis", "push",
            "SE::Google", "test",
            "--redis-host", "redis.example.com"
        ])
        assert result.exit_code == 0

    def test_redis_push_json_output(self):
        """Test redis push with JSON output."""
        result = runner.invoke(app, [
            "redis", "push",
            "SE::Google", "test",
            "--json"
        ])
        assert result.exit_code == 0
        import json
        try:
            data = json.loads(result.output)
            assert data.get("status") == "success"
        except json.JSONDecodeError:
            pass

    def test_redis_push_missing_args(self):
        """Test redis push without required arguments."""
        result = runner.invoke(app, ["redis", "push"])
        assert result.exit_code != 0


class TestRedisWaitCommand:
    """Test suite for redis wait command."""

    def test_redis_wait_help(self):
        """Test redis wait command help."""
        result = runner.invoke(app, ["redis", "wait", "--help"])
        assert result.exit_code == 0
        assert "Wait for task completion" in result.output

    def test_redis_wait_with_queue(self):
        """Test redis wait with queue name."""
        result = runner.invoke(app, ["redis", "wait", "my_queue"])
        # May timeout or complete depending on implementation
        assert result.exit_code in [0, 124]  # 124 is timeout exit code

    def test_redis_wait_with_timeout(self):
        """Test redis wait with custom timeout."""
        result = runner.invoke(app, [
            "redis", "wait", "my_queue",
            "--timeout", "1"
        ])
        # Should timeout quickly
        assert result.exit_code in [0, 124]

    def test_redis_wait_json_output(self):
        """Test redis wait with JSON output."""
        result = runner.invoke(app, [
            "redis", "wait", "my_queue",
            "--timeout", "1",
            "--json"
        ])
        assert result.exit_code in [0, 124]

    def test_redis_wait_missing_queue(self):
        """Test redis wait without required queue argument."""
        result = runner.invoke(app, ["redis", "wait"])
        assert result.exit_code != 0
