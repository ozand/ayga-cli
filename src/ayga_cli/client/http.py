"""HTTP API client for ayga_parser."""

import json
from typing import Any, Optional

import httpx

from ayga_cli.config import AygaParserConfig
from ayga_cli.exceptions import (
    AygaParserAPIError,
    AygaParserAuthError,
    AygaParserHTTPError,
    AygaParserProxyError,
    AygaParserServerError,
    AygaParserTimeoutError,
    AygaParserValidationError,
)
from ayga_cli.utils.error_helper import parse_api_error


class AygaParserHttpClient:
    """Async HTTP client for ayga_parser API.

    This client wraps all ayga_parser HTTP API methods using httpx.AsyncClient.
    It handles authentication, error mapping, and provides typed interfaces
    for all API operations.

    Args:
        config: AygaParserConfig instance with connection settings
        timeout: Request timeout in seconds (overrides config.default_timeout)

    Example:
        >>> config = AygaParserConfig(password=SecretStr("secret"))
        >>> client = AygaParserHttpClient(config)
        >>> await client.ping()
        True
    """

    def __init__(
        self,
        config: Optional[AygaParserConfig] = None,
        timeout: Optional[int] = None,
    ):
        self.config = config or AygaParserConfig()
        self.timeout = timeout or self.config.default_timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._basic_auth = self._build_basic_auth()

    def _build_basic_auth(self) -> Optional[httpx.BasicAuth]:
        """Build HTTP Basic Auth configuration if credentials are available."""
        credentials = self.config.get_http_basic_auth()
        if not credentials:
            return None
        username, password = credentials
        return httpx.BasicAuth(username, password)

    async def __aenter__(self) -> "AygaParserHttpClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Initialize the HTTP client connection."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.http_url,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                auth=self._basic_auth,
            )

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _ensure_connected(self) -> httpx.AsyncClient:
        """Ensure client is connected and return the client instance."""
        if self._client is None:
            raise AygaParserHTTPError("Client not connected. Use 'async with' or call connect()")
        return self._client

    def _build_payload(self, action: str, data: Optional[dict] = None) -> dict:
        """Build the standard API request payload.

        Args:
            action: API action name (e.g., 'ping', 'oneRequest')
            data: Optional action-specific data

        Returns:
            Complete payload dictionary with password
        """
        password = self.config.get_password()
        if not password:
            raise AygaParserAuthError("ayga_parser password not configured")

        payload: dict[str, Any] = {
            "password": password,
            "action": action,
        }
        if data is not None:
            payload["data"] = data
        return payload

    def _extract_error_message(self, result: dict[str, Any]) -> str:
        """Extract a meaningful error message from an API response."""
        return (
            result.get("error")
            or result.get("msg")
            or result.get("message")
            or "Unknown API error"
        )

    def _coerce_parsers_list(self, data: Any) -> list[dict[str, Any]]:
        """Normalize parser list payloads to a list of parser dictionaries."""
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]

        if isinstance(data, dict):
            parsers = data.get("parsers")
            if isinstance(parsers, list):
                return [item for item in parsers if isinstance(item, dict)]

            if parsers is None:
                items = []
                for name, info in data.items():
                    if isinstance(info, dict):
                        item = {"name": name, **info}
                    else:
                        item = {"name": str(info)}
                    items.append(item)
                return items

        return []

    def _static_parser_list(self) -> list[dict[str, Any]]:
        """Build a parser list from the bundled static manifest."""
        from ayga_cli.static_manifest import STATIC_PARSERS

        return [
            {
                "name": parser.parser,
                "description": parser.description,
                "category": parser.category,
                "source": "static",
            }
            for parser in STATIC_PARSERS.values()
        ]

    async def _request(
        self,
        action: str,
        data: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> dict:
        """Make an API request and handle errors.

        Args:
            action: API action name
            data: Optional request data
            timeout: Optional override for request timeout

        Returns:
            Parsed JSON response

        Raises:
            AygaParserHTTPError: For HTTP-level errors
            AygaParserAPIError: For API-level errors in response
            AygaParserTimeoutError: For timeout errors
            AygaParserAuthError: For authentication failures
        """
        client = self._ensure_connected()
        payload = self._build_payload(action, data)

        request_timeout = timeout or self.timeout

        try:
            response = await client.post(
                ".",
                json=payload,
                timeout=request_timeout,
            )
            response.raise_for_status()
        except httpx.TimeoutException as e:
            raise AygaParserTimeoutError(
                f"Request timeout after {request_timeout}s for action '{action}'"
            ) from e
        except httpx.HTTPStatusError as e:
            raise AygaParserHTTPError(
                message=f"HTTP error: {e}",
                status_code=e.response.status_code,
                response_body=e.response.text,
                action=action,
            ) from e
        except httpx.HTTPError as e:
            raise AygaParserHTTPError(
                message=f"HTTP request failed: {e}",
                action=action,
            ) from e

        # Parse response
        try:
            result = response.json()
        except json.JSONDecodeError as e:
            raise AygaParserHTTPError(
                message=f"Invalid JSON response: {e}",
                status_code=response.status_code,
                response_body=response.text,
                action=action,
            ) from e

        # Check for API-level errors
        if not result.get("success", True):
            error_msg = self._extract_error_message(result)
            error_code = result.get("code")

            # Parse error for actionable recommendations
            error_info = parse_api_error(result)

            # Determine specific error type based on error content
            error_text = " ".join(str(log) for log in error_info.get("full_logs", [])).lower()

            # Check for proxy-related errors
            if any(pattern in error_text for pattern in ["proxy", "eof", "connection refused"]):
                raise AygaParserProxyError(
                    message=error_info["message"],
                    code=error_code,
                    data=result,
                    error_info=error_info,
                )

            # Check for server errors (5xx)
            if error_code and error_code >= 500:
                raise AygaParserServerError(
                    message=error_info["message"],
                    code=error_code,
                    data=result,
                    error_info=error_info,
                )

            raise AygaParserAPIError(
                message=error_info["message"],
                code=error_code,
                data=result,
                error_info=error_info,
            )

        return result

    # =================================================================
    # API Methods
    # =================================================================

    async def ping(self) -> bool:
        """Check if ayga_parser API is accessible.

        Returns:
            True if API responds successfully

        Raises:
            AygaParserHTTPError: If HTTP request fails
            AygaParserAPIError: If API returns an error
        """
        result = await self._request("ping")
        data = result.get("data")
        if isinstance(data, str):
            return data.lower() == "pong"
        return bool(result.get("success", False))

    async def one_request(
        self,
        parser: str,
        query: str,
        preset: Optional[str] = None,
        config_preset: Optional[str] = None,
        options: Optional[list[dict]] = None,
        query_builders: Optional[list[dict]] = None,
        results_builders: Optional[list[dict]] = None,
        unique_only: bool = False,
        timeout: Optional[int] = None,
    ) -> dict:
        """Execute a single synchronous parsing request.

        This method blocks until the parsing is complete and returns
        the full result. Suitable for small, quick queries.

        Args:
            parser: Parser name (e.g., 'SE::Google', 'Net::Whois')
            query: Query string to parse
            preset: Parser preset name (default: config.default_preset)
            config_preset: Config preset for thread pool (default: config.default_config_preset)
            options: List of option overrides (e.g., [{"id": "pagecount", "value": 1}])
            query_builders: Query builder configurations
            results_builders: Results builder configurations
            unique_only: Whether to return only unique results
            timeout: Request timeout override

        Returns:
            API response containing results

        Raises:
            AygaParserValidationError: If required parameters are missing
            AygaParserTimeoutError: If request times out
            AygaParserAPIError: If API returns an error
        """
        if not parser:
            raise AygaParserValidationError("Parser name is required")
        if not query:
            raise AygaParserValidationError("Query is required")

        data: dict[str, Any] = {
            "parser": parser,
            "preset": preset or self.config.default_preset,
            "query": query,
            "configPreset": config_preset or self.config.default_config_preset,
            "uniqueOnly": unique_only,
        }

        if options:
            data["options"] = options
        if query_builders:
            data["queryBuilders"] = query_builders
        if results_builders:
            data["resultsBuilders"] = results_builders

        return await self._request("oneRequest", data, timeout=timeout)

    async def bulk_request(
        self,
        parser: str,
        queries: list[str],
        preset: Optional[str] = None,
        config_preset: Optional[str] = None,
        options: Optional[list[dict]] = None,
        query_builders: Optional[list[dict]] = None,
        results_builders: Optional[list[dict]] = None,
        unique_only: bool = False,
        threads: int = 5,
        timeout: Optional[int] = None,
    ) -> dict:
        """Execute batch synchronous parsing for multiple queries.

        Args:
            parser: Parser name (e.g., 'SE::Google')
            queries: List of query strings to parse
            preset: Parser preset name
            config_preset: Config preset for thread pool
            options: List of option overrides
            query_builders: Query builder configurations
            results_builders: Results builder configurations
            unique_only: Whether to return only unique results
            threads: Number of threads to use (default: 5)
            timeout: Request timeout override

        Returns:
            API response containing results for all queries

        Raises:
            AygaParserValidationError: If required parameters are missing
            AygaParserTimeoutError: If request times out
            AygaParserAPIError: If API returns an error
        """
        if not parser:
            raise AygaParserValidationError("Parser name is required")
        if not queries:
            raise AygaParserValidationError("At least one query is required")

        data: dict[str, Any] = {
            "parser": parser,
            "preset": preset or self.config.default_preset,
            "queries": queries,
            "configPreset": config_preset or self.config.default_config_preset,
            "uniqueOnly": unique_only,
            "threads": threads,
        }

        if options:
            data["options"] = options
        if query_builders:
            data["queryBuilders"] = query_builders
        if results_builders:
            data["resultsBuilders"] = results_builders

        return await self._request("bulkRequest", data, timeout=timeout)

    async def get_parsers_list(self) -> list[dict]:
        """Get list of all available parsers.

        Returns:
            List of parser metadata dictionaries containing:
            - name: Parser name (e.g., 'SE::Google')
            - description: Human-readable description
            - category: Parser category

        Raises:
            AygaParserHTTPError: If HTTP request fails
            AygaParserAPIError: If API returns an error
        """
        try:
            result = await self._request("getParsersList")
            parsers = self._coerce_parsers_list(result.get("data", []))
            if parsers:
                return parsers
        except AygaParserAPIError:
            pass

        return self._static_parser_list()

    async def get_parser_info(self, parser: str) -> dict:
        """Get detailed information about a specific parser.

        Args:
            parser: Parser name (e.g., 'SE::Google')

        Returns:
            Parser metadata including:
            - name: Parser name
            - description: Description
            - options: Available configuration options
            - results: Result field definitions

        Raises:
            AygaParserValidationError: If parser name is empty
            AygaParserHTTPError: If HTTP request fails
            AygaParserAPIError: If API returns an error
        """
        if not parser:
            raise AygaParserValidationError("Parser name is required")

        data = {"parser": parser}
        result = await self._request("getParserInfo", data)
        return result.get("data", {})

    async def get_tasks_list(
        self,
        active_only: bool = False,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Get list of tasks/jobs from ayga_parser.

        Args:
            active_only: If True, return only active/running tasks
            limit: Maximum number of tasks to return

        Returns:
            List of task dictionaries containing:
            - id: Task ID
            - parser: Parser name
            - status: Task status
            - progress: Completion percentage
            - created: Creation timestamp

        Raises:
            AygaParserHTTPError: If HTTP request fails
            AygaParserAPIError: If API returns an error
        """
        data: dict[str, Any] = {}
        if active_only:
            data["activeOnly"] = True
        if limit:
            data["limit"] = limit

        result = await self._request("getTasksList", data if data else None)
        return result.get("data", [])

    async def get_task_info(self, task_id: str) -> dict:
        """Get detailed information about a specific task.

        Args:
            task_id: Task identifier

        Returns:
            Task details including status, progress, and results

        Raises:
            AygaParserValidationError: If task_id is empty
            AygaParserHTTPError: If HTTP request fails
            AygaParserAPIError: If API returns an error
        """
        if not task_id:
            raise AygaParserValidationError("Task ID is required")

        data = {"taskId": task_id}
        result = await self._request("getTaskInfo", data)
        return result.get("data", {})

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task.

        Args:
            task_id: Task identifier to cancel

        Returns:
            True if cancellation was successful

        Raises:
            AygaParserValidationError: If task_id is empty
            AygaParserHTTPError: If HTTP request fails
            AygaParserAPIError: If API returns an error
        """
        if not task_id:
            raise AygaParserValidationError("Task ID is required")

        data = {"taskId": task_id}
        result = await self._request("cancelTask", data)
        return result.get("success", False)

    async def get_presets_list(self) -> list[dict]:
        """Get list of available parser presets.

        Returns:
            List of preset dictionaries containing:
            - name: Preset name
            - parser: Associated parser
            - description: Preset description

        Raises:
            AygaParserHTTPError: If HTTP request fails
            AygaParserAPIError: If API returns an error
        """
        result = await self._request("getPresetsList")
        return result.get("data", [])

    async def get_config_presets_list(self) -> list[dict]:
        """Get list of available config presets (thread pool configurations).

        Returns:
            List of config preset dictionaries

        Raises:
            AygaParserHTTPError: If HTTP request fails
            AygaParserAPIError: If API returns an error
        """
        result = await self._request("getConfigPresetsList")
        return result.get("data", [])

    async def get_results(
        self,
        task_id: str,
        format_type: str = "json",
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> dict:
        """Get results from a completed task.

        Args:
            task_id: Task identifier
            format_type: Output format ('json', 'csv', 'txt')
            offset: Result offset for pagination
            limit: Maximum number of results to return

        Returns:
            Results data in requested format

        Raises:
            AygaParserValidationError: If task_id is empty
            AygaParserHTTPError: If HTTP request fails
            AygaParserAPIError: If API returns an error
        """
        if not task_id:
            raise AygaParserValidationError("Task ID is required")

        data: dict[str, Any] = {
            "taskId": task_id,
            "format": format_type,
            "offset": offset,
        }
        if limit:
            data["limit"] = limit

        result = await self._request("getResults", data)
        return result.get("data", {})

    async def get_proxies(self) -> dict:
        """Get proxy pool status.

        Returns:
            Dictionary with proxy counts per checker

        Raises:
            AygaParserHTTPError: If HTTP request fails
            AygaParserAPIError: If API returns an error
        """
        result = await self._request("getProxies")
        return result.get("data", {})
