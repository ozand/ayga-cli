"""Exceptions package for ayga-cli."""

from ayga_cli.exceptions.exit_codes import (
    SUCCESS,
    ERROR_GENERAL,
    ERROR_TIMEOUT,
    ERROR_NOT_FOUND,
    ERROR_UNAVAILABLE,
    ERROR_INPUT,
    DESCRIPTIONS,
)

__all__ = [
    "SUCCESS", "ERROR_GENERAL", "ERROR_TIMEOUT",
    "ERROR_NOT_FOUND", "ERROR_UNAVAILABLE", "ERROR_INPUT",
    "DESCRIPTIONS",
]


# Legacy exception classes — kept for http.py compatibility
class AygaParserError(Exception):
    """Base exception for ayga-cli."""
    status_code: int = 0

    def __init__(self, message="", **kwargs):
        super().__init__(message)
        self.message = message
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self):
        parts = [self.message]
        if self.status_code:
            parts.append(f"status={self.status_code}")
        return " ".join(parts)


class AygaParserAPIError(AygaParserError):
    """API-level error."""


class AygaParserAuthError(AygaParserAPIError):
    """Authentication error."""


class AygaParserHTTPError(AygaParserAPIError):
    """HTTP transport error."""


class AygaParserProxyError(AygaParserAPIError):
    """Proxy error."""


class AygaParserServerError(AygaParserAPIError):
    """Server-side error."""


class AygaParserTimeoutError(AygaParserAPIError):
    """Timeout error."""


class AygaParserValidationError(AygaParserAPIError):
    """Validation error."""
