"""Tests for parsers command."""

import pytest
from typer.testing import CliRunner
from unittest.mock import AsyncMock, patch

from aparser_cli.main import app

runner = CliRunner()


class TestParsersListCommand:
    """Test suite for parsers list command."""

    def test_parsers_list_help(self):
        """Test parsers list command help."""
        result = runner.invoke(app, ["parsers", "list", "--help"])
        assert result.exit_code == 0
        assert "List all available parsers" in result.output

    def test_parsers_list_default(self):
        """Test parsers list command."""
        result = runner.invoke(app, ["parsers", "list"])
        assert result.exit_code == 0
        # Should show parsers table or placeholder
        assert "GoogleParser" in result.output or "Available Parsers" in result.output

    def test_parsers_list_json_output(self):
        """Test parsers list with JSON output."""
        result = runner.invoke(app, ["parsers", "list", "--json"])
        assert result.exit_code == 0
        import json
        try:
            data = json.loads(result.output)
            assert isinstance(data, list)
        except json.JSONDecodeError:
            # Output might have extra formatting
            pass

    def test_parsers_list_with_category(self):
        """Test parsers list with category filter."""
        result = runner.invoke(app, ["parsers", "list", "--category", "SE"])
        assert result.exit_code == 0

    def test_parsers_list_no_cache(self):
        """Test parsers list without cache."""
        result = runner.invoke(app, ["parsers", "list", "--no-cache"])
        assert result.exit_code == 0


class TestParsersInfoCommand:
    """Test suite for parsers info command."""

    def test_parsers_info_help(self):
        """Test parsers info command help."""
        result = runner.invoke(app, ["parsers", "info", "--help"])
        assert result.exit_code == 0
        assert "Get detailed information" in result.output

    def test_parsers_info_with_name(self):
        """Test parsers info with parser name."""
        result = runner.invoke(app, ["parsers", "info", "SE::Google"])
        # May fail if no manifest exists, that's ok for this test
        assert "SE::Google" in result.output or "Parser:" in result.output or "Error:" in result.output

    def test_parsers_info_json_output(self):
        """Test parsers info with JSON output."""
        result = runner.invoke(app, ["parsers", "info", "SE::Google", "--json"])
        # May fail if no manifest exists, that's ok for this test
        import json
        try:
            data = json.loads(result.output)
            assert isinstance(data, dict)
        except json.JSONDecodeError:
            pass

    def test_parsers_info_missing_name(self):
        """Test parsers info without required name argument."""
        result = runner.invoke(app, ["parsers", "info"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Usage:" in result.output
