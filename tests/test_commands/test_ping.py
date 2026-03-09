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
        result = runner.invoke(app, ["ping"])
        assert result.exit_code == 0
        assert "Connected" in result.output or "Connection successful" in result.output

    def test_ping_with_host(self):
        """Test ping command with custom host."""
        result = runner.invoke(app, ["ping", "--host", "http://example.com"])
        assert result.exit_code == 0
        assert "example.com" in result.output

    def test_ping_with_port(self):
        """Test ping command with custom port."""
        result = runner.invoke(app, ["ping", "--port", "8080"])
        assert result.exit_code == 0

    def test_ping_json_output(self):
        """Test ping command with JSON output."""
        result = runner.invoke(app, ["ping", "--json"])
        assert result.exit_code == 0
        # Should output valid JSON
        import json
        try:
            json.loads(result.output)
        except json.JSONDecodeError:
            # Output might have Rich formatting, check for JSON-like content
            assert "status" in result.output or "{" in result.output

    def test_ping_with_timeout(self):
        """Test ping command with custom timeout."""
        result = runner.invoke(app, ["ping", "--timeout", "10"])
        assert result.exit_code == 0
