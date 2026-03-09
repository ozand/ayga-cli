"""Static manifest with popular A-Parser parsers and their defaults.

This module provides a static manifest of commonly used parsers with their
required overrides and default configurations. Used when API manifest is
unavailable or for quick reference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ParserDefaults:
    """Default overrides and configuration for a parser."""

    parser: str
    description: str
    category: str
    required_overrides: list[str] = field(default_factory=list)
    default_overrides: dict[str, Any] = field(default_factory=dict)
    examples: list[dict[str, str]] = field(default_factory=list)
    notes: str = ""


# Static manifest of popular parsers with their defaults
STATIC_PARSERS: dict[str, ParserDefaults] = {
    # FreeAI parsers
    "FreeAI::Perplexity": ParserDefaults(
        parser="FreeAI::Perplexity",
        description="Perplexity AI search and answer parser",
        category="FreeAI",
        required_overrides=["proxyChecker"],
        default_overrides={
            "proxyChecker": "reproxy_v4",
            "timeout": 120,
            "useproxy": True,
        },
        examples=[
            {"query": "business applications of AI", "desc": "Basic search"},
            {"query": "latest news in technology", "overrides": "depth=5", "desc": "With depth override"},
            {"query": "market analysis", "overrides": "timeout=180,retries=3", "desc": "With custom timeout"},
        ],
        notes="Requires reproxy_v4 proxy checker for reliable operation",
    ),
    "FreeAI::ChatGPT": ParserDefaults(
        parser="FreeAI::ChatGPT",
        description="ChatGPT-based text generation and completion",
        category="FreeAI",
        required_overrides=["proxyChecker"],
        default_overrides={
            "proxyChecker": "reproxy_v4",
            "timeout": 120,
            "useproxy": True,
        },
        examples=[
            {"query": "Explain quantum computing", "desc": "Basic question"},
            {"query": "Write a Python function", "overrides": "max_tokens=500", "desc": "With token limit"},
        ],
        notes="Requires reproxy_v4 proxy checker",
    ),
    "FreeAI::Claude": ParserDefaults(
        parser="FreeAI::Claude",
        description="Claude AI text generation",
        category="FreeAI",
        required_overrides=["proxyChecker"],
        default_overrides={
            "proxyChecker": "reproxy_v4",
            "timeout": 120,
            "useproxy": True,
        },
        examples=[
            {"query": "Summarize this article", "desc": "Basic summarization"},
        ],
        notes="Requires reproxy_v4 proxy checker",
    ),

    # Search Engine parsers
    "SE::Google": ParserDefaults(
        parser="SE::Google",
        description="Google search results parser",
        category="SE",
        required_overrides=[],
        default_overrides={
            "pagecount": 1,
            "timeout": 60,
        },
        examples=[
            {"query": "machine learning tutorials", "desc": "Basic search"},
            {"query": "best restaurants in NYC", "overrides": "pagecount=3,region=us", "desc": "Multi-page US results"},
            {"query": "python programming", "overrides": "depth=10,unique=true", "desc": "Deep search with dedup"},
        ],
        notes="Supports pagination with pagecount override",
    ),
    "SE::Yandex": ParserDefaults(
        parser="SE::Yandex",
        description="Yandex search results parser",
        category="SE",
        required_overrides=[],
        default_overrides={
            "pagecount": 1,
            "timeout": 60,
        },
        examples=[
            {"query": "продвижение сайтов", "desc": "Russian SEO query"},
        ],
        notes="Best for Russian language searches",
    ),
    "SE::Bing": ParserDefaults(
        parser="SE::Bing",
        description="Bing search results parser",
        category="SE",
        required_overrides=[],
        default_overrides={
            "pagecount": 1,
            "timeout": 60,
        },
        examples=[
            {"query": "cloud computing services", "desc": "Basic search"},
        ],
        notes="Good alternative to Google",
    ),

    # Network/Whois parsers
    "Net::Whois": ParserDefaults(
        parser="Net::Whois",
        description="WHOIS domain information lookup",
        category="Net",
        required_overrides=[],
        default_overrides={
            "timeout": 30,
        },
        examples=[
            {"query": "example.com", "desc": "Basic WHOIS lookup"},
            {"query": "google.com", "overrides": "timeout=60", "desc": "With extended timeout"},
        ],
        notes="Returns domain registration details",
    ),
    "Net::DNS": ParserDefaults(
        parser="Net::DNS",
        description="DNS records lookup",
        category="Net",
        required_overrides=[],
        default_overrides={
            "timeout": 30,
        },
        examples=[
            {"query": "example.com", "desc": "Get all DNS records"},
            {"query": "google.com", "overrides": "type=MX", "desc": "MX records only"},
        ],
        notes="Supports A, MX, NS, TXT, CNAME record types",
    ),

    # Social Media parsers
    "Social::Instagram": ParserDefaults(
        parser="Social::Instagram",
        description="Instagram profile and post parser",
        category="Social",
        required_overrides=["proxyChecker"],
        default_overrides={
            "proxyChecker": "reproxy_v4",
            "timeout": 90,
            "useproxy": True,
        },
        examples=[
            {"query": "nasa", "desc": "Profile info"},
            {"query": "#travel", "overrides": "limit=50", "desc": "Hashtag search"},
        ],
        notes="Requires proxy for rate limit handling",
    ),
    "Social::Twitter": ParserDefaults(
        parser="Social::Twitter",
        description="Twitter/X profile and tweet parser",
        category="Social",
        required_overrides=["proxyChecker"],
        default_overrides={
            "proxyChecker": "reproxy_v4",
            "timeout": 90,
            "useproxy": True,
        },
        examples=[
            {"query": "elonmusk", "desc": "Profile tweets"},
            {"query": "AI news", "overrides": "limit=100", "desc": "Search tweets"},
        ],
        notes="Requires proxy for reliable access",
    ),

    # E-commerce parsers
    "Ecom::Amazon": ParserDefaults(
        parser="Ecom::Amazon",
        description="Amazon product search and details",
        category="Ecom",
        required_overrides=["proxyChecker"],
        default_overrides={
            "proxyChecker": "reproxy_v4",
            "timeout": 90,
            "useproxy": True,
        },
        examples=[
            {"query": "wireless headphones", "desc": "Product search"},
            {"query": "B08HMWZBXC", "overrides": "type=asin", "desc": "ASIN lookup"},
        ],
        notes="Supports both search and ASIN lookups",
    ),

    # Utility parsers
    "Util::HTML": ParserDefaults(
        parser="Util::HTML",
        description="Generic HTML page parser",
        category="Util",
        required_overrides=[],
        default_overrides={
            "timeout": 60,
        },
        examples=[
            {"query": "https://example.com", "desc": "Parse single page"},
            {"query": "https://news.ycombinator.com", "overrides": "selector=.titleline>a", "desc": "With CSS selector"},
        ],
        notes="Use CSS selectors to extract specific elements",
    ),
    "Util::JSON": ParserDefaults(
        parser="Util::JSON",
        description="JSON API response parser",
        category="Util",
        required_overrides=[],
        default_overrides={
            "timeout": 60,
        },
        examples=[
            {"query": "https://api.example.com/data", "desc": "Parse JSON endpoint"},
            {"query": "https://api.github.com/users/github", "overrides": "path=name,login", "desc": "Extract specific fields"},
        ],
        notes="Use 'path' override to extract nested fields",
    ),
}


def get_parser_defaults(parser: str) -> Optional[ParserDefaults]:
    """Get default configuration for a parser.

    Args:
        parser: Parser name (e.g., 'FreeAI::Perplexity')

    Returns:
        ParserDefaults if found, None otherwise
    """
    return STATIC_PARSERS.get(parser)


def list_parsers(category: Optional[str] = None) -> list[ParserDefaults]:
    """List all parsers in the static manifest.

    Args:
        category: Optional category filter

    Returns:
        List of ParserDefaults
    """
    parsers = list(STATIC_PARSERS.values())
    if category:
        parsers = [p for p in parsers if p.category == category]
    return sorted(parsers, key=lambda p: p.parser)


def get_required_overrides(parser: str) -> list[str]:
    """Get required overrides for a parser.

    Args:
        parser: Parser name

    Returns:
        List of required override keys
    """
    defaults = get_parser_defaults(parser)
    if defaults:
        return defaults.required_overrides
    return []


def get_default_overrides(parser: str) -> dict[str, Any]:
    """Get default overrides for a parser.

    Args:
        parser: Parser name

    Returns:
        Dict of default override key-value pairs
    """
    defaults = get_parser_defaults(parser)
    if defaults:
        return defaults.default_overrides.copy()
    return {}


def validate_overrides(parser: str, overrides: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate that all required overrides are present.

    Args:
        parser: Parser name
        overrides: Dict of override key-value pairs

    Returns:
        Tuple of (is_valid, list_of_missing_overrides)
    """
    required = get_required_overrides(parser)
    missing = [r for r in required if r not in overrides]
    return len(missing) == 0, missing


def get_parser_examples(parser: str) -> list[dict[str, str]]:
    """Get usage examples for a parser.

    Args:
        parser: Parser name

    Returns:
        List of example dicts with 'query', 'overrides', 'desc' keys
    """
    defaults = get_parser_defaults(parser)
    if defaults:
        return defaults.examples
    return []


def format_example(parser: str, example: dict[str, str]) -> str:
    """Format an example as a command string.

    Args:
        parser: Parser name
        example: Example dict with 'query', 'overrides', 'desc'

    Returns:
        Formatted command string
    """
    query = example.get("query", "")
    overrides = example.get("overrides", "")

    if overrides:
        return f'aparser run {parser} "{query}" --options "{overrides}"'
    else:
        return f'aparser run {parser} "{query}"'


def get_all_categories() -> list[str]:
    """Get all unique categories in the static manifest.

    Returns:
        Sorted list of category names
    """
    categories = set(p.category for p in STATIC_PARSERS.values())
    return sorted(list(categories))
