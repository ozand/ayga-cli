"""Pagination utilities for auto-fetching multi-page results.

Handles automatic pagination for parsers that return paginated results.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Callable, Coroutine, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class PaginationHandler:
    """Handles automatic pagination for multi-page results.

    Automatically detects truncated results and queues additional pages
    until all results are collected or max_pages is reached.

    Attributes:
        parser: Parser name
        query: Base query string
        max_pages: Maximum number of pages to fetch
        page_param: Name of the pagination option parameter
    """

    def __init__(
        self,
        parser: str,
        query: str,
        max_pages: int = 10,
        page_param: str = "page",
        pagecount_param: str = "pagecount",
    ):
        self.parser = parser
        self.query = query
        self.max_pages = max_pages
        self.page_param = page_param
        self.pagecount_param = pagecount_param
        self.results: list[dict] = []
        self.page_count = 0

    def is_truncated(self, result: dict) -> bool:
        """Check if results indicate more pages available.

        Args:
            result: API response result

        Returns:
            True if more pages likely exist
        """
        # Check various indicators of truncation
        data = result.get("data", {})

        # Check if results array exists and has items
        results_array = data.get("results", [])
        if not results_array:
            return False

        # Check for explicit pagination info
        pagination = data.get("pagination", {})
        if pagination:
            current = pagination.get("current_page", 1)
            total = pagination.get("total_pages", 1)
            return current < total

        # Check for has_more flag
        if data.get("has_more", False):
            return True

        # Check if we got a full page (likely more available)
        page_size = len(results_array)
        if page_size >= 10:  # Assuming standard page size
            return True

        return False

    def build_page_options(
        self,
        base_options: list[dict],
        page: int,
    ) -> list[dict]:
        """Build options for specific page.

        Args:
            base_options: Base options from user
            page: Page number to fetch

        Returns:
            Options list with pagination parameter
        """
        options = list(base_options)

        # Update or add page parameter
        page_found = False
        for opt in options:
            if opt.get("id") == self.page_param:
                opt["value"] = page
                page_found = True
                break

        if not page_found:
            options.append({"id": self.page_param, "value": page})

        # Ensure pagecount is set to 1 for individual page requests
        pagecount_found = False
        for opt in options:
            if opt.get("id") == self.pagecount_param:
                opt["value"] = 1
                pagecount_found = True
                break

        if not pagecount_found:
            options.append({"id": self.pagecount_param, "value": 1})

        return options

    def merge_results(self, page_results: list[dict]) -> None:
        """Merge page results into combined results.

        Args:
            page_results: Results from a single page
        """
        self.results.extend(page_results)

    def get_combined_results(self) -> dict[str, Any]:
        """Get all combined results.

        Returns:
            Dictionary with all results and metadata
        """
        return {
            "results": self.results,
            "pages_fetched": self.page_count,
            "total_items": len(self.results),
            "parser": self.parser,
            "query": self.query,
        }


async def execute_with_pagination(
    execute_fn: Callable[..., Coroutine[Any, Any, dict]],
    parser: str,
    query: str,
    base_options: Optional[list[dict]] = None,
    max_pages: int = 10,
    preset: str = "default",
    show_progress: bool = True,
) -> dict[str, Any]:
    """Execute parser with automatic pagination.

    Fetches page 1, checks if results are truncated, and auto-queues
    pages 2 through N until all results are collected.

    Args:
        execute_fn: Async function to execute parser request
        parser: Parser name
        query: Query string
        base_options: Base options for parser
        max_pages: Maximum pages to fetch
        preset: Preset name
        show_progress: Show progress indicator

    Returns:
        Combined results from all pages

    Example:
        >>> async def execute_request(parser, query, options):
        ...     # Your execution logic here
        ...     return {"data": {"results": [...]}}
        >>>
        >>> results = await execute_with_pagination(
        ...     execute_request,
        ...     "SE::Google",
        ...     "test query",
        ...     max_pages=5
        ... )
    """
    handler = PaginationHandler(
        parser=parser,
        query=query,
        max_pages=max_pages,
    )

    base_options = base_options or []

    async def fetch_page(page: int) -> dict:
        """Fetch a single page."""
        options = handler.build_page_options(base_options, page)
        return await execute_fn(
            parser=parser,
            query=query,
            preset=preset,
            options=options,
        )

    if show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Fetching pages from {parser}...",
                total=None,
            )

            # Fetch first page
            progress.update(task, description=f"Fetching page 1/{max_pages}...")
            result = await fetch_page(1)
            handler.page_count = 1

            # Extract results from response
            data = result.get("data", {})
            page_results = data.get("results", [])
            handler.merge_results(page_results)

            # Check for more pages
            current_page = 1
            while handler.is_truncated(result) and current_page < max_pages:
                current_page += 1
                progress.update(
                    task,
                    description=f"Fetching page {current_page}/{max_pages}...",
                )

                result = await fetch_page(current_page)
                handler.page_count = current_page

                data = result.get("data", {})
                page_results = data.get("results", [])
                handler.merge_results(page_results)

                # Break if no more results
                if not page_results:
                    break

            progress.update(task, description="Complete!")
    else:
        # Fetch without progress indicator
        result = await fetch_page(1)
        handler.page_count = 1

        data = result.get("data", {})
        page_results = data.get("results", [])
        handler.merge_results(page_results)

        current_page = 1
        while handler.is_truncated(result) and current_page < max_pages:
            current_page += 1
            result = await fetch_page(current_page)
            handler.page_count = current_page

            data = result.get("data", {})
            page_results = data.get("results", [])
            handler.merge_results(page_results)

            if not page_results:
                break

    return handler.get_combined_results()


async def execute_paginated_stream(
    execute_fn: Callable[..., Coroutine[Any, Any, dict]],
    parser: str,
    query: str,
    base_options: Optional[list[dict]] = None,
    max_pages: int = 10,
    preset: str = "default",
) -> AsyncIterator[dict]:
    """Execute parser with pagination and yield results as they arrive.

    Yields individual result items as pages are fetched.

    Args:
        execute_fn: Async function to execute parser request
        parser: Parser name
        query: Query string
        base_options: Base options for parser
        max_pages: Maximum pages to fetch
        preset: Preset name

    Yields:
        Individual result items

    Example:
        >>> async for item in execute_paginated_stream(
        ...     execute_request,
        ...     "SE::Google",
        ...     "test query"
        ... ):
        ...     print(item)
    """
    handler = PaginationHandler(
        parser=parser,
        query=query,
        max_pages=max_pages,
    )

    base_options = base_options or []

    async def fetch_page(page: int) -> dict:
        options = handler.build_page_options(base_options, page)
        return await execute_fn(
            parser=parser,
            query=query,
            preset=preset,
            options=options,
        )

    # Fetch first page
    result = await fetch_page(1)
    handler.page_count = 1

    data = result.get("data", {})
    page_results = data.get("results", [])

    for item in page_results:
        yield item

    # Fetch additional pages
    current_page = 1
    while handler.is_truncated(result) and current_page < max_pages:
        current_page += 1
        result = await fetch_page(current_page)
        handler.page_count = current_page

        data = result.get("data", {})
        page_results = data.get("results", [])

        for item in page_results:
            yield item

        if not page_results:
            break
