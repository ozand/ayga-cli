"""
Redis Queue Client for ayga_parser async operations.

Provides async Redis-based communication with ayga_parser instances,
implementing the primary transport layer for job queuing and result retrieval.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis
from ayga_cli.proxy_strategy import merge_with_proxy

logger = logging.getLogger(__name__)


class AygaParserRedisClient:
    """
    Async Redis client for ayga_parser queue operations.

    Implements lazy connection to Redis and provides methods for:
    - Pushing jobs to ayga_parser queue (LPUSH)
    - Retrieving results from result queues (BLPOP)
    - Checking queue depths

    Args:
        redis_host: Redis server hostname (default: 127.0.0.1)
        redis_port: Redis server port (default: 6379)
        redis_queue: Main ayga_parser queue name (default: ayga_parser_redis_api)
        redis_password: Optional Redis AUTH password
        password: ayga_parser API password for request authentication
    """

    def __init__(
        self,
        redis_host: str = "127.0.0.1",
        redis_port: int = 6379,
        redis_queue: str = "ayga_parser_redis_api",
        redis_password: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_queue = redis_queue
        self.redis_password = redis_password
        self.password = password

        self._redis: Optional[Redis] = None

    async def _get_redis(self) -> Redis:
        """
        Lazy initialization of Redis connection.

        Returns:
            Redis: Async Redis client instance
        """
        if self._redis is None:
            self._redis = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                decode_responses=True,
                socket_timeout=360,
                socket_connect_timeout=15,
            )
            logger.debug(f"Connected to Redis at {self.redis_host}:{self.redis_port}")
        return self._redis

    async def close(self) -> None:
        """Close Redis connection if open."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
            logger.debug("Redis connection closed")

    async def __aenter__(self) -> AygaParserRedisClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    def _build_request(
        self,
        parser: str,
        query: str,
        preset: str = "default",
        config_preset: str = "default",
        result_queue: Optional[str] = None,
        options: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """
        Build ayga_parser request payload.

        Args:
            parser: Parser name (e.g., "SE::Google")
            query: Search query or target
            preset: Parser preset name
            config_preset: Config preset (thread pool settings)
            result_queue: Custom result queue name (default: auto-generated)
            options: List of option overrides

        Returns:
            dict: Formatted request payload for ayga_parser
        """
        data: dict[str, Any] = {
            "parser": parser,
            "preset": preset,
            "configPreset": config_preset,
            "query": query,
        }

        if result_queue:
            data["resultQueue"] = result_queue

        if options:
            data["options"] = options

        return {
            "password": self.password,
            "action": "oneRequest",
            "data": data,
        }

    async def push(
        self,
        parser: str,
        query: str,
        preset: str = "default",
        config_preset: str = "default",
        result_queue: Optional[str] = None,
        options: Optional[list[dict[str, Any]]] = None,
        as_list: bool = False,
    ) -> str:
        """
        Push a job to the ayga_parser Redis queue.

        Uses LPUSH to add the job to the main ayga_parser queue.
        ayga_parser will process it and push results to the specified result queue.

        Args:
            parser: Parser name (e.g., "SE::Google", "Net::Whois")
            query: Search query, URL, or target to parse
            preset: Parser preset name (default: "default")
            config_preset: Config preset for thread pool settings (default: "default")
            result_queue: Custom result queue name. If None, ayga_parser uses default.
            options: List of option overrides, e.g., [{"id": "pagecount", "value": 5}]
            as_list: If True, serialize as a 6-element JSON array [query_id, parser, preset, query, overrides, api_opts] (preferred for API::Server::Redis worker tasks).

        Returns:
            str: The result queue name where results will be delivered

        Raises:
            redis.RedisError: If Redis operation fails
            ValueError: If parser or query is empty
        """
        if not parser:
            raise ValueError("Parser name cannot be empty")
        if not query:
            raise ValueError("Query cannot be empty")

        r = await self._get_redis()
        actual_result_queue = result_queue or f"ayga_parser_results_{parser.replace('::', '_')}"

        if as_list:
            import time
            query_id = f"q_{parser.replace('::', '_').lower()}_{int(time.time() * 1000)}"
            
            options = merge_with_proxy(parser, options or [])
            
            # Convert options list [{"id": k, "value": v}] to dictionary for the 6-element list overrides
            override_opts = {}
            if options:
                for opt in options:
                    if isinstance(opt, dict) and "id" in opt and "value" in opt:
                        override_opts[opt["id"]] = opt["value"]
            
            # Build apiOpts. We put output_queue here so that A-Parser writes to the unified queue
            api_opts = {"output_queue": actual_result_queue}
            
            # Build 6-element array: [query_id, parser, preset, query, overrides, api_opts]
            request_data = [
                query_id,
                parser,
                preset,
                query,
                override_opts,
                api_opts
            ]
            request_json = json.dumps(request_data, ensure_ascii=False)
        else:
            request = self._build_request(
                parser=parser,
                query=query,
                preset=preset,
                config_preset=config_preset,
                result_queue=result_queue,
                options=options,
            )
            request_json = json.dumps(request, ensure_ascii=False)

        await r.lpush(self.redis_queue, request_json)

        logger.debug(
            f"Pushed job to queue '{self.redis_queue}' (as_list={as_list}): "
            f"parser={parser}, query={query[:50]}..., result_queue={actual_result_queue}"
        )

        return actual_result_queue

    async def pop(
        self,
        result_queue: str,
        timeout: int = 300,
    ) -> Optional[dict[str, Any]]:
        """
        Pop a result from the specified result queue.

        Uses BLPOP for blocking retrieval with timeout.
        Waits until a result is available or timeout expires.

        Args:
            result_queue: Name of the result queue to listen on
            timeout: Maximum seconds to wait (0 = block indefinitely)

        Returns:
            dict: Parsed result JSON, or None if timeout expired

        Raises:
            redis.RedisError: If Redis operation fails
            json.JSONDecodeError: If result is not valid JSON
            ValueError: If result_queue is empty

        Example:
            >>> client = AygaParserRedisClient(password="secret")
            >>> result = await client.pop("my_results", timeout=60)
            >>> if result:
            ...     print(f"Got {len(result.get('results', []))} results")
            ... else:
            ...     print("Timeout - no results yet")
        """
        if not result_queue:
            raise ValueError("Result queue name cannot be empty")

        r = await self._get_redis()

        logger.debug(f"Waiting for result from queue '{result_queue}' (timeout={timeout}s)")

        result = await r.blpop(result_queue, timeout=timeout)

        if result is None:
            logger.debug(f"Timeout waiting for result from queue '{result_queue}'")
            return None

        # BLPOP returns tuple: (queue_name, value)
        _, result_json = result

        try:
            parsed = json.loads(result_json)
            logger.debug(f"Received result from queue '{result_queue}'")
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse result JSON from queue '{result_queue}': {e}")
            raise

    async def queue_depth(self, queue_name: str) -> int:
        """
        Get the current depth (length) of a Redis queue.

        Args:
            queue_name: Name of the queue to check

        Returns:
            int: Number of items in the queue

        Raises:
            redis.RedisError: If Redis operation fails
            ValueError: If queue_name is empty

        Example:
            >>> client = AygaParserRedisClient(password="secret")
            >>> pending = await client.queue_depth("ayga_parser_redis_api")
            >>> print(f"{pending} jobs waiting to be processed")
        """
        if not queue_name:
            raise ValueError("Queue name cannot be empty")

        r = await self._get_redis()

        depth = await r.llen(queue_name)

        logger.debug(f"Queue '{queue_name}' depth: {depth}")

        return depth

    async def health_check(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            bool: True if Redis is reachable, False otherwise
        """
        try:
            r = await self._get_redis()
            await r.ping()
            return True
        except redis.RedisError as e:
            logger.warning(f"Redis health check failed: {e}")
            return False
