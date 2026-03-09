"""Utility modules for A-Parser CLI."""

from aparser_cli.utils.dry_run import DryRunSimulator, print_dry_run_summary
from aparser_cli.utils.error_helper import (
    ERROR_PATTERNS,
    PARSER_DOCS,
    format_error_for_cli,
    get_proxy_recommendation,
    parse_api_error,
)
from aparser_cli.utils.pagination import PaginationHandler, execute_with_pagination

__all__ = [
    "DryRunSimulator",
    "print_dry_run_summary",
    "PaginationHandler",
    "execute_with_pagination",
    "parse_api_error",
    "format_error_for_cli",
    "get_proxy_recommendation",
    "ERROR_PATTERNS",
    "PARSER_DOCS",
]
