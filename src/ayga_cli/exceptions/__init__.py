"""ayga_parser CLI custom exceptions."""

from typing import Optional


class ayga_parserError(Exception):
    """Base exception for all ayga_parser CLI errors."""
    pass


class AygaParserConfigError(ayga_parserError):
    """Configuration-related errors."""
    pass


class AygaParserHTTPError(ayga_parserError):
    """HTTP API errors.

    Attributes:
        message: Error message
        status_code: HTTP status code (if available)
        response_body: Raw response body (if available)
        action: API action that was being performed
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        action: str | None = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        self.action = action

    def __str__(self) -> str:
        parts = [self.message]
        if self.action:
            parts.append(f"(action: {self.action})")
        if self.status_code:
            parts.append(f"HTTP {self.status_code}")
        if self.response_body:
            parts.append(f"Response: {self.response_body[:200]}")
        return " | ".join(parts)


class AygaParserAPIError(ayga_parserError):
    """ayga_parser API returned an error response.

    This is raised when the HTTP call succeeds but the API returns
    an error in the response body.
    """

    def __init__(
        self,
        message: str,
        code: int | None = None,
        data: dict | None = None,
        error_info: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data or {}
        self.error_info = error_info or {}

    def __str__(self) -> str:
        if self.code:
            return f"API Error {self.code}: {self.message}"
        return f"API Error: {self.message}"

    def get_formatted_error(self, verbose: bool = False) -> str:
        """Get formatted error message with recommendations.

        Args:
            verbose: Whether to include full logs

        Returns:
            Formatted error string
        """
        from ayga_cli.utils.error_helper import format_error_for_cli
        return format_error_for_cli(self.error_info, verbose=verbose)


class AygaParserAuthError(ayga_parserError):
    """Authentication/authorization errors."""
    pass


class ayga_parserRedisError(ayga_parserError):
    """Redis connection or operation errors."""
    pass


class AygaParserTimeoutError(ayga_parserError):
    """Timeout errors for blocking operations."""
    pass


class AygaParserValidationError(ayga_parserError):
    """Input validation errors."""
    pass


class AygaParserProxyError(AygaParserAPIError):
    """Proxy-related API errors with actionable recommendations."""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        data: dict | None = None,
        error_info: dict | None = None,
        parser_name: Optional[str] = None,
    ):
        super().__init__(message, code, data, error_info)
        self.parser_name = parser_name


class AygaParserServerError(AygaParserAPIError):
    """Server-side errors (5xx) with context."""
    pass
