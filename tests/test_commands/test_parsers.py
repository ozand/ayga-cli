"""Tests for parsers command."""

import pytest
from ayga_cli.manifest import Manifest, ParserInfo
from typer.testing import CliRunner
from unittest.mock import AsyncMock, patch

from ayga_cli.main import app

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
        manifest = Manifest(
            parsers={
                "SE::Google": ParserInfo(name="SE::Google", description="Google parser", category="SE", presets=["default"])
            }
        )
        with patch("ayga_cli.commands.parsers._load_manifest_with_fallback", return_value=manifest):
            result = runner.invoke(app, ["parsers", "list"])
        assert result.exit_code == 0
        assert "SE::Google" in result.output

    def test_parsers_list_json_output(self):
        """Test parsers list with JSON output."""
        manifest = Manifest(
            parsers={
                "SE::Google": ParserInfo(name="SE::Google", description="Google parser", category="SE", presets=["default"])
            }
        )
        with patch("ayga_cli.commands.parsers._load_manifest_with_fallback", return_value=manifest):
            result = runner.invoke(app, ["parsers", "list", "--json"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_parsers_list_with_category(self):
        """Test parsers list with category filter."""
        manifest = Manifest(
            parsers={
                "SE::Google": ParserInfo(name="SE::Google", description="Google parser", category="SE", presets=["default"])
            }
        )
        with patch("ayga_cli.commands.parsers._load_manifest_with_fallback", return_value=manifest):
            result = runner.invoke(app, ["parsers", "list", "--category", "SE"])
        assert result.exit_code == 0

    def test_parsers_list_no_cache(self):
        """Test parsers list without cache."""
        manifest = Manifest(
            parsers={
                "SE::Google": ParserInfo(name="SE::Google", description="Google parser", category="SE", presets=["default"])
            }
        )
        with patch("ayga_cli.commands.parsers._load_manifest_with_fallback", return_value=manifest):
            result = runner.invoke(app, ["parsers", "list", "--no-cache"])
        assert result.exit_code == 0

    def test_parsers_search_falls_back_to_static_manifest(self):
        """Test parser search using fallback manifest."""
        result = runner.invoke(app, ["parsers", "search", "google"])
        assert result.exit_code == 0
        assert "SE::Google" in result.output


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
        assert "SE::Google" in result.output

    def test_parsers_info_json_output(self):
        """Test parsers info with JSON output."""
        result = runner.invoke(app, ["parsers", "info", "SE::Google", "--json"])
        import json
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_parsers_info_missing_name(self):
        """Test parsers info without required name argument."""
        result = runner.invoke(app, ["parsers", "info"])
        assert result.exit_code != 0
        assert "Parser name is required" in result.output or "Usage:" in result.output
