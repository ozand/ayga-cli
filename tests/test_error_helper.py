"""Tests for error helper module."""

import pytest

from aparser_cli.utils.error_helper import (
    ERROR_PATTERNS,
    PARSER_DOCS,
    format_error_for_cli,
    get_proxy_recommendation,
    parse_api_error,
)


class TestParseApiError:
    """Tests for parse_api_error function."""

    def test_proxy_eof_error(self):
        """Test parsing proxy EOF error."""
        response_data = {
            "success": False,
            "logs": [
                "Parser FreeAI::Perplexity::0 parse query test",
                "Use proxy http://23.148.152.46:80",
                "POST(1): https://www.perplexity.ai/...",
                "HTTPS(C) Proxy: Error: EOF",
            ],
        }

        result = parse_api_error(response_data, parser_name="FreeAI::Perplexity")

        assert result["message"] == "Proxy connection failed"
        assert "proxyChecker" in result["recommendation"]
        assert "reproxy_v4" in result["example"]
        assert result["docs_link"] == PARSER_DOCS["FreeAI::Perplexity"]
        assert len(result["full_logs"]) == 4

    def test_proxy_read_error_eof(self):
        """Test parsing proxy read error EOF."""
        response_data = {
            "success": False,
            "logs": [
                "Parser FreeAI::Perplexity::0 parse query test",
                "Proxy: Error: Read error: EOF",
            ],
        }

        result = parse_api_error(response_data)

        assert result["message"] == "Proxy connection failed"
        assert "proxyChecker" in result["recommendation"]

    def test_500_internal_server_error(self):
        """Test parsing 500 internal server error."""
        response_data = {
            "success": False,
            "error": "500 Internal Server Error",
            "logs": [
                "Parser SE::Google::0 parse query test",
                "500 Internal Server Error",
            ],
        }

        result = parse_api_error(response_data)

        assert result["message"] == "Server error (possibly proxy-related)"
        assert "proxy settings" in result["recommendation"]
        # Without parser_name and with non-matching parser in logs, should get generic docs
        assert result["docs_link"] == "https://a-parser.com/docs"

    def test_500_error_with_parser_context(self):
        """Test parsing 500 error with parser context adds specific docs."""
        response_data = {
            "success": False,
            "error": "500 Internal Server Error",
            "logs": [
                "Parser FreeAI::Perplexity::0 parse query test",
                "500 Internal Server Error",
            ],
        }

        result = parse_api_error(response_data, parser_name="FreeAI::Perplexity")

        assert result["message"] == "Server error (possibly proxy-related)"
        # With parser_name, should get parser-specific docs link
        assert result["docs_link"] == PARSER_DOCS["FreeAI::Perplexity"]

    def test_timeout_error(self):
        """Test parsing timeout error."""
        response_data = {
            "success": False,
            "logs": [
                "Parser FreeAI::Perplexity::0 parse query test",
                "Request timeout after 60s",
            ],
        }

        result = parse_api_error(response_data)

        assert result["message"] == "Request timed out"
        assert "timeout" in result["recommendation"]
        assert "timeout=180" in result["example"]

    def test_unknown_error_with_explicit_error(self):
        """Test parsing unknown error with explicit error field."""
        response_data = {
            "success": False,
            "error": "Some custom error message",
            "logs": [],
        }

        result = parse_api_error(response_data)

        assert result["message"] == "Some custom error message"
        assert result["docs_link"] == "https://a-parser.com/docs"

    def test_unknown_error_with_logs(self):
        """Test parsing unknown error with only logs."""
        response_data = {
            "success": False,
            "logs": ["Something unexpected happened"],
        }

        result = parse_api_error(response_data)

        assert result["message"] == "Something unexpected happened"

    def test_parser_specific_docs(self):
        """Test that parser-specific docs are included."""
        response_data = {
            "success": False,
            "logs": ["Some error"],
        }

        result = parse_api_error(response_data, parser_name="FreeAI::ChatGPT")

        assert result["docs_link"] == PARSER_DOCS["FreeAI::ChatGPT"]

    def test_nested_data_logs(self):
        """Test extracting logs from nested data structure."""
        response_data = {
            "success": False,
            "data": {
                "logs": [
                    "Parser FreeAI::Perplexity::0 parse query test",
                    "Proxy: Error: Read error: EOF",
                ],
            },
        }

        result = parse_api_error(response_data)

        assert result["message"] == "Proxy connection failed"
        assert len(result["full_logs"]) == 2


class TestFormatErrorForCli:
    """Tests for format_error_for_cli function."""

    def test_basic_formatting(self):
        """Test basic error formatting."""
        error_info = {
            "message": "Proxy connection failed",
            "recommendation": "Try specifying proxyChecker override",
            "example": 'aparser run FreeAI::Perplexity "query" --overrides "proxyChecker=reproxy_v4"',
            "docs_link": "https://a-parser.com/docs/parsers/freeai-perplexity",
            "full_logs": ["log1", "log2"],
        }

        result = format_error_for_cli(error_info, verbose=False)

        assert "❌ Error: Proxy connection failed" in result
        assert "💡 Recommendation:" in result
        assert "📋 Example:" in result
        assert "📖 Documentation:" in result
        assert "log1" not in result  # Logs not shown without verbose

    def test_verbose_formatting(self):
        """Test verbose error formatting with logs."""
        error_info = {
            "message": "Proxy connection failed",
            "recommendation": "Try specifying proxyChecker override",
            "example": 'aparser run ...',
            "docs_link": "https://example.com/docs",
            "full_logs": [
                "[0] Parser FreeAI::Perplexity::0 parse query test",
                "[1] Use proxy http://23.148.152.46:80",
            ],
        }

        result = format_error_for_cli(error_info, verbose=True)

        assert "❌ Error: Proxy connection failed" in result
        assert "Full logs:" in result
        assert "[0]" in result
        assert "[1]" in result

    def test_formatting_without_optional_fields(self):
        """Test formatting without optional fields."""
        error_info = {
            "message": "Some error",
            "recommendation": "Some recommendation",
            "example": None,
            "docs_link": None,
            "full_logs": [],
        }

        result = format_error_for_cli(error_info, verbose=False)

        assert "❌ Error: Some error" in result
        assert "💡 Recommendation: Some recommendation" in result
        assert "📋 Example:" not in result
        assert "📖 Documentation:" not in result


class TestGetProxyRecommendation:
    """Tests for get_proxy_recommendation function."""

    def test_perplexity_recommendation(self):
        """Test recommendation for Perplexity parser."""
        result = get_proxy_recommendation("FreeAI::Perplexity")

        assert "FreeAI::Perplexity" in result
        assert "proxyChecker=reproxy_v4" in result

    def test_chatgpt_recommendation(self):
        """Test recommendation for ChatGPT parser."""
        result = get_proxy_recommendation("FreeAI::ChatGPT")

        assert "FreeAI::ChatGPT" in result
        assert "proxyChecker" in result

    def test_generic_recommendation(self):
        """Test generic recommendation for unknown parser."""
        result = get_proxy_recommendation("Some::Parser")

        assert "proxyChecker" in result
        assert "your_checker" in result

    def test_no_parser_recommendation(self):
        """Test recommendation without parser name."""
        result = get_proxy_recommendation(None)

        assert "proxyChecker" in result


class TestErrorPatterns:
    """Tests for ERROR_PATTERNS constant."""

    def test_all_patterns_have_message(self):
        """Test that all error patterns have a message."""
        for pattern, info in ERROR_PATTERNS.items():
            assert "message" in info
            assert isinstance(info["message"], str)

    def test_all_patterns_have_recommendation(self):
        """Test that all error patterns have a recommendation."""
        for pattern, info in ERROR_PATTERNS.items():
            assert "recommendation" in info
            assert isinstance(info["recommendation"], str)


class TestParserDocs:
    """Tests for PARSER_DOCS constant."""

    def test_common_parsers_have_docs(self):
        """Test that common parsers have documentation links."""
        common_parsers = [
            "FreeAI::Perplexity",
            "FreeAI::ChatGPT",
            "SE::Google",
            "SE::Yandex",
            "Net::Whois",
        ]

        for parser in common_parsers:
            assert parser in PARSER_DOCS
            assert PARSER_DOCS[parser].startswith("https://")
