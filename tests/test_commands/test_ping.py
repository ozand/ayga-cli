"""Tests for ping command."""

import pytest
from typer.testing import CliRunner
from unittest.mock import AsyncMock, patch, MagicMock

from aparser_cli.main import app

runner = CliRunner()


class TestPingCommand:
    """Test suite for ping command."""

    def test_ping_help(self):
        """Test ping command help."""
        result = runner.invoke(app, ["ping", "--help"])
        assert result.exit_code == 0
        assert "Test HTTP connection" in result.output

    def test_ping_default(self):
        """Test ping command with default options."""
        with patch("aparser_cli.commands.ping._ping_backend", new=AsyncMock(return_value={
            "status": "ok",
            "reachable": True,
            "message": "A-Parser API responded with pong",
            "http_url": "http://localhost:9091/API",
            "basic_auth_enabled": True,
            "basic_auth_username": "",
        })):
            result = runner.invoke(app, ["ping"])
        assert result.exit_code == 0
        assert "A-Parser API responded with pong" in result.output

    def test_ping_with_host(self):
        """Test ping command with custom host."""
        with patch("aparser_cli.commands.ping._ping_backend", new=AsyncMock(return_value={
            "status": "ok",
            "reachable": True,
            "message": "A-Parser API responded with pong",
            "http_url": "http://example.com:9091/API",
            "basic_auth_enabled": False,
            "basic_auth_username": None,
        })):
            result = runner.invoke(app, ["ping", "--host", "http://example.com", "--port", "9091"])
        assert result.exit_code == 0
        assert "example.com:9091/API" in result.output

    def test_ping_with_port(self):
        """Test ping command with custom port."""
        with patch("aparser_cli.commands.ping._ping_backend", new=AsyncMock(return_value={
            "status": "ok",
            "reachable": True,
            "message": "A-Parser API responded with pong",
            "http_url": "http://127.0.0.1:8080/API",
            "basic_auth_enabled": False,
            "basic_auth_username": None,
        })):
            result = runner.invoke(app, ["ping", "--host", "http://127.0.0.1", "--port", "8080"])
        assert result.exit_code == 0

    def test_ping_json_output(self):
        """Test ping command with JSON output."""
        with patch("aparser_cli.commands.ping._ping_backend", new=AsyncMock(return_value={
            "status": "ok",
            "reachable": True,
            "message": "A-Parser API responded with pong",
            "http_url": "http://localhost:9091/API",
            "basic_auth_enabled": True,
            "basic_auth_username": "",
        })):
            result = runner.invoke(app, ["ping", "--json"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert data["reachable"] is True

    def test_ping_with_timeout(self):
        """Test ping command with custom timeout."""
        with patch("aparser_cli.commands.ping._ping_backend", new=AsyncMock(return_value={
            "status": "ok",
            "reachable": True,
            "message": "A-Parser API responded with pong",
            "http_url": "http://localhost:9091/API",
            "basic_auth_enabled": False,
            "basic_auth_username": None,
        })) as ping_backend:
            result = runner.invoke(app, ["ping", "--timeout", "10"])
        assert result.exit_code == 0
        assert ping_backend.await_count == 1
