"""Error parsing and recommendations for ayga-parser API errors."""

from typing import Optional

# Error patterns and their actionable recommendations
ERROR_PATTERNS = {
    "Proxy: Error: Read error: EOF": {
        "message": "Proxy connection failed",
        "recommendation": "Try specifying proxyChecker override",
        "example": 'ayga-parser run FreeAI::Perplexity "query" --overrides "proxyChecker=reproxy_v4"',
    },
    "HTTPS(C) Proxy: Error: EOF": {
        "message": "Proxy connection failed",
        "recommendation": "Try specifying proxyChecker override",
        "example": 'ayga-parser run FreeAI::Perplexity "query" --overrides "proxyChecker=reproxy_v4"',
    },
    "Proxy: Error: Connection refused": {
        "message": "Proxy connection refused",
        "recommendation": "The proxy server is not accepting connections. Try a different proxy or proxyChecker",
        "example": 'ayga-parser run FreeAI::Perplexity "query" --overrides "proxyChecker=reproxy_v4"',
    },
    "500 Internal Server Error": {
        "message": "Server error (possibly proxy-related)",
        "recommendation": "Check proxy settings or try different proxyChecker",
        "docs_link": "https://ayga-parser.com/docs",
    },
    "timeout": {
        "message": "Request timed out",
        "recommendation": "Increase timeout override",
        "example": 'ayga-parser run ... --overrides "timeout=180"',
    },
    "Timeout": {
        "message": "Request timed out",
        "recommendation": "Increase timeout override",
        "example": 'ayga-parser run ... --overrides "timeout=180"',
    },
    "Connection timeout": {
        "message": "Connection timed out",
        "recommendation": "Increase timeout override or check network connectivity",
        "example": 'ayga-parser run ... --overrides "timeout=180"',
    },
    "Read timeout": {
        "message": "Read operation timed out",
        "recommendation": "Increase timeout override",
        "example": 'ayga-parser run ... --overrides "timeout=180"',
    },
    "Unauthorized": {
        "message": "Authentication failed",
        "recommendation": "Check your ayga-parser password configuration",
        "example": "ayga-parser config set password YOUR_PASSWORD",
    },
    "Invalid parser": {
        "message": "Parser not found or invalid",
        "recommendation": "Check parser name or use 'ayga-parser parsers list-static' to see available parsers",
        "example": "ayga-parser parsers info FreeAI::Perplexity",
    },
    "rate limit": {
        "message": "Rate limit exceeded",
        "recommendation": "Wait before making more requests or reduce request frequency",
    },
    "Rate limit": {
        "message": "Rate limit exceeded",
        "recommendation": "Wait before making more requests or reduce request frequency",
    },
}

# Parser-specific documentation links
PARSER_DOCS = {
    "FreeAI::Perplexity": "https://ayga-parser.com/docs/parsers/freeai-perplexity",
    "FreeAI::ChatGPT": "https://ayga-parser.com/docs/parsers/freeai-chatgpt",
    "SE::Google": "https://ayga-parser.com/docs/parsers/se-google",
    "SE::Yandex": "https://ayga-parser.com/docs/parsers/se-yandex",
    "Net::Whois": "https://ayga-parser.com/docs/parsers/net-whois",
}


def parse_api_error(response_data: dict, parser_name: Optional[str] = None) -> dict:
    """Parse error from API response and return actionable info.

    Args:
        response_data: The API response data containing error information
        parser_name: Optional parser name for context-specific recommendations

    Returns:
        Dictionary with parsed error information including:
        - message: Human-readable error message
        - recommendation: Actionable recommendation
        - example: Example command (if applicable)
        - docs_link: Link to relevant documentation (if applicable)
        - full_logs: Full log entries for verbose output
    """
    result = {
        "message": "Unknown error",
        "recommendation": "Check logs for more details",
        "example": None,
        "docs_link": None,
        "full_logs": [],
    }

    # Extract logs from response
    logs = response_data.get("logs", [])
    if not logs and "data" in response_data:
        logs = response_data.get("data", {}).get("logs", [])

    result["full_logs"] = logs

    # Build error text from logs for pattern matching
    error_text = " ".join(str(log) for log in logs).lower()
    original_error_text = " ".join(str(log) for log in logs)

    # Check for known error patterns
    for pattern, info in ERROR_PATTERNS.items():
        if pattern.lower() in error_text or pattern in original_error_text:
            result["message"] = info["message"]
            result["recommendation"] = info["recommendation"]
            result["example"] = info.get("example")
            result["docs_link"] = info.get("docs_link")
            break

    # If no pattern matched, try to extract error from response
    if result["message"] == "Unknown error":
        # Check for explicit error message in response
        if "error" in response_data:
            result["message"] = str(response_data["error"])
        elif "message" in response_data:
            result["message"] = str(response_data["message"])
        elif logs:
            # Use last log entry as error message
            result["message"] = str(logs[-1])

    # Add parser-specific documentation link if available
    # Parser-specific docs take precedence over generic error pattern docs
    if parser_name and parser_name in PARSER_DOCS:
        result["docs_link"] = PARSER_DOCS[parser_name]

    # General documentation link as fallback
    if not result["docs_link"]:
        result["docs_link"] = "https://ayga-parser.com/docs"

    return result


def format_error_for_cli(
    error_info: dict,
    verbose: bool = False,
    parser_name: Optional[str] = None,
) -> str:
    """Format error information for CLI output.

    Args:
        error_info: Dictionary from parse_api_error()
        verbose: Whether to include full logs
        parser_name: Optional parser name for context

    Returns:
        Formatted error string for display
    """
    lines = []

    # Main error message
    lines.append(f"❌ Error: {error_info['message']}")

    # Recommendation
    if error_info.get("recommendation"):
        lines.append(f"💡 Recommendation: {error_info['recommendation']}")

    # Example command
    if error_info.get("example"):
        lines.append(f"📋 Example: {error_info['example']}")

    # Documentation link
    if error_info.get("docs_link"):
        lines.append(f"📖 Documentation: {error_info['docs_link']}")

    # Full logs (only in verbose mode)
    if verbose and error_info.get("full_logs"):
        lines.append("")
        lines.append("Full logs:")
        for i, log in enumerate(error_info["full_logs"]):
            lines.append(f"  [{i}] {log}")

    return "\n".join(lines)


def get_proxy_recommendation(parser_name: Optional[str] = None) -> str:
    """Get proxy-related recommendation for a parser.

    Args:
        parser_name: Name of the parser being used

    Returns:
        Recommendation string for proxy configuration
    """
    if parser_name == "FreeAI::Perplexity":
        return (
            "FreeAI::Perplexity requires a specific proxyChecker. "
            "Use: --overrides 'proxyChecker=reproxy_v4'"
        )
    elif parser_name == "FreeAI::ChatGPT":
        return (
            "FreeAI::ChatGPT may require specific proxy settings. "
            "Try: --overrides 'proxyChecker=reproxy_v4'"
        )
    else:
        return (
            "If using proxies, ensure proxyChecker is properly configured. "
            "Use: --overrides 'proxyChecker=your_checker'"
        )
