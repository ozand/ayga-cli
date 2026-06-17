"""
Redis Queue Client for Redis Wrapper async operations.

Provides async Redis-based communication with Redis Wrapper instances,
implementing the primary transport layer for job queuing and result retrieval.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class AygaParserRedisClient:
    """
    Async Redis client for Redis Wrapper queue operations.

    Implements lazy connection to Redis and provides methods for:
    - Pushing jobs to Redis queue (LPUSH)
    - Retrieving results from result queues (BLPOP)
    - Checking queue depths
    - Retrieving available sources

    Args:
        redis_host: Redis server hostname (default: 127.0.0.1)
        redis_port: Redis server port (default: 6379)
        redis_queue: Main Redis Wrapper queue name (default: ayga_parser_redis_api)
        redis_password: Optional Redis AUTH password
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
        [DEPRECATED] Build ayga_parser request payload.
        This method is for internal backwards compatibility only.

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
        source: str,
        query: str,
        job_id: Optional[str] = None,
        result_queue: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Push a job to the Redis queue.

        Uses LPUSH to add the job to the main Redis queue.
        The Redis Wrapper will process it and push results to the specified result queue.

        Args:
            source: Abstract source name (e.g., "web-search", "ai-answer")
            query: Search query, URL, or target
            job_id: Optional job ID (default: auto-generated ayga_{source}_{timestamp_ms})
            result_queue: Custom result queue name (default: auto-generated ayga_results_{job_id})
            metadata: Optional dictionary of extra fields to pass through to Redis Wrapper

        Returns:
            str: The result queue name where results will be delivered

        Raises:
            redis.RedisError: If Redis operation fails
            ValueError: If source or query is empty
        """
        if not source:
            raise ValueError("Source name cannot be empty")
        if not query:
            raise ValueError("Query cannot be empty")

        r = await self._get_redis()
        
        import time
        timestamp_ms = int(time.time() * 1000)
        
        actual_job_id = job_id or f"ayga_{source.replace('-', '_')}_{timestamp_ms}"
        actual_result_queue = result_queue or f"ayga_results_{actual_job_id}"
        actual_metadata = metadata or {}
        
        api_opts = {"output_queue": actual_result_queue}
        
        # Build 6-element array: [job_id, source, query, metadata, api_opts, {}]
        request_data = [
            actual_job_id,
            source,
            query,
            actual_metadata,
            api_opts,
            {}
        ]
        request_json = json.dumps(request_data, ensure_ascii=False)

        await r.lpush(self.redis_queue, request_json)

        logger.debug(
            f"Pushed job to queue '{self.redis_queue}': "
            f"source={source}, query={query[:50]}..., result_queue={actual_result_queue}"
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

    async def get_sources(self, sources_queue: str = "ayga_sources") -> list[dict]:
        """
        Get the list of available sources from the Redis Wrapper.
        
        Args:
            sources_queue: Name of the sources queue on Redis (default: "ayga_sources")
            
        Returns:
            list[dict]: List of available sources, or empty list if none found
        """
        r = await self._get_redis()
        items = await r.lrange(sources_queue, 0, -1)
        
        if not items:
            return []
            
        sources = []
        for item in items:
            try:
                sources.append(json.loads(item))
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode source item: {item}")
                
        return sources

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
