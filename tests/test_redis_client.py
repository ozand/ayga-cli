"""Tests for ayga_parser Redis client."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from ayga_cli.client.redis import AygaParserRedisClient


class TestAygaParserRedisClient:
    """Test suite for AygaParserRedisClient."""

    def test_init_default_values(self):
        """Test client initialization with default values."""
        client = AygaParserRedisClient(password="test_pass")
        assert client.redis_host == "127.0.0.1"
        assert client.redis_port == 6379
        assert client.redis_queue == "ayga_parser_redis_api"
        assert client.redis_password is None
        assert client.password == "test_pass"
        assert client._redis is None

    def test_init_custom_values(self):
        """Test client initialization with custom values."""
        client = AygaParserRedisClient(
            redis_host="redis.example.com",
            redis_port=6380,
            redis_queue="custom_queue",
            redis_password="redis_pass",
            password="api_pass",
        )
        assert client.redis_host == "redis.example.com"
        assert client.redis_port == 6380
        assert client.redis_queue == "custom_queue"
        assert client.redis_password == "redis_pass"
        assert client.password == "api_pass"

    @pytest.mark.asyncio
    async def test_get_redis_lazy_init(self):
        """Test lazy Redis connection initialization."""
        with patch("redis.asyncio.Redis") as MockRedis:
            mock_redis = AsyncMock()
            MockRedis.return_value = mock_redis
            
            client = AygaParserRedisClient(password="test")
            redis_instance = await client._get_redis()
            
            assert redis_instance is not None
            assert client._redis is not None
            MockRedis.assert_called_once_with(
                host="127.0.0.1",
                port=6379,
                password=None,
                decode_responses=True,
                socket_timeout=360,
                socket_connect_timeout=15,
            )

    @pytest.mark.asyncio
    async def test_get_redis_reuse_connection(self):
        """Test that Redis connection is reused."""
        with patch("redis.asyncio.Redis") as MockRedis:
            mock_redis = AsyncMock()
            MockRedis.return_value = mock_redis
            
            client = AygaParserRedisClient(password="test")
            redis1 = await client._get_redis()
            redis2 = await client._get_redis()
            
            assert redis1 is redis2
            MockRedis.assert_called_once()  # Only called once

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing Redis connection."""
        with patch("redis.asyncio.Redis") as MockRedis:
            mock_redis = AsyncMock()
            MockRedis.return_value = mock_redis
            
            client = AygaParserRedisClient(password="test")
            await client._get_redis()
            await client.close()
            
            mock_redis.close.assert_called_once()
            assert client._redis is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        with patch("redis.asyncio.Redis") as MockRedis:
            mock_redis = AsyncMock()
            mock_redis.close = AsyncMock()  # redis-py uses close(), not aclose()
            MockRedis.return_value = mock_redis
            
            async with AygaParserRedisClient(password="test") as client:
                assert client is not None
                # Trigger connection creation so close() will be called
                await client._get_redis()
            
            # Redis client uses close() for async close
            mock_redis.close.assert_called_once()


class TestAygaParserRedisClientPush:
    """Test suite for Redis push operations."""

    @pytest.mark.asyncio
    async def test_push_success(self, mock_redis):
        """Test successful Redis LPUSH."""
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient(password="test_pass")
            result_queue = await client.push(
                source="web-search",
                query="test query",
            )
            
            assert result_queue.startswith("ayga_results_ayga_web_search_")
            mock_redis.lpush.assert_called_once()
            
            # Verify the pushed data
            call_args = mock_redis.lpush.call_args
            assert call_args[0][0] == "ayga_parser_redis_api"  # queue name
            # Second arg is JSON string
            pushed_data = json.loads(call_args[0][1])
            # Should be a 6-element list: [job_id, source, query, metadata, api_opts, {}]
            assert isinstance(pushed_data, list)
            assert len(pushed_data) == 6
            assert pushed_data[1] == "web-search"
            assert pushed_data[2] == "test query"
            assert isinstance(pushed_data[3], dict)
            assert pushed_data[4]["output_queue"] == result_queue

    @pytest.mark.asyncio
    async def test_push_with_custom_result_queue(self, mock_redis):
        """Test push with custom result queue."""
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient(password="test_pass")
            result_queue = await client.push(
                source="ai-answer",
                query="test",
                result_queue="my_q",
            )
            
            assert result_queue == "my_q"
            pushed_data = json.loads(mock_redis.lpush.call_args[0][1])
            assert pushed_data[4]["output_queue"] == "my_q"

    @pytest.mark.asyncio
    async def test_push_with_job_id(self, mock_redis):
        """Test push with job_id."""
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient(password="test_pass")
            
            await client.push(
                source="web-search",
                query="test",
                job_id="my_job_123",
            )
            
            pushed_data = json.loads(mock_redis.lpush.call_args[0][1])
            assert pushed_data[0] == "my_job_123"
            assert pushed_data[4]["output_queue"] == "ayga_results_my_job_123"

    @pytest.mark.asyncio
    async def test_push_empty_source_raises(self, mock_redis):
        """Test push with empty parser raises error."""
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient(password="test_pass")
            
            with pytest.raises(ValueError) as exc_info:
                await client.push(source="", query="test")
            assert "Source name cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_push_empty_query_raises(self, mock_redis):
        """Test push with empty query raises error."""
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient(password="test_pass")
            
            with pytest.raises(ValueError) as exc_info:
                await client.push(source="web-search", query="")
            assert "Query cannot be empty" in str(exc_info.value)


class TestAygaParserRedisClientSources:
    """Test suite for Redis sources operations."""

    @pytest.mark.asyncio
    async def test_get_sources_returns_list(self, mock_redis):
        """Test successful Redis LRANGE for sources."""
        mock_redis.lrange.return_value = [
            '{"name": "web-search", "description": "Web Search"}',
            '{"name": "ai-answer", "description": "AI Answer"}'
        ]
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient()
            sources = await client.get_sources()
            assert len(sources) == 2
            assert sources[0]["name"] == "web-search"
            assert sources[1]["name"] == "ai-answer"

    @pytest.mark.asyncio
    async def test_get_sources_empty(self, mock_redis):
        """Test successful Redis LRANGE for empty sources."""
        mock_redis.lrange.return_value = []
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient()
            sources = await client.get_sources()
            assert sources == []

class TestAygaParserRedisClientPop:
    """Test suite for Redis pop operations."""

    @pytest.mark.asyncio
    async def test_pop_success(self, mock_redis):
        """Test successful Redis BLPOP."""
        mock_redis.blpop.return_value = (
            "result_queue",
            json.dumps({"success": 1, "data": {"resultString": "test result"}}),
        )
        
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient(password="test_pass")
            result = await client.pop("result_queue", timeout=10)
            
            assert result["success"] == 1
            assert result["data"]["resultString"] == "test result"
            mock_redis.blpop.assert_called_once_with("result_queue", timeout=10)

    @pytest.mark.asyncio
    async def test_pop_timeout(self, mock_redis):
        """Test pop with timeout (no result)."""
        mock_redis.blpop.return_value = None
        
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient(password="test_pass")
            result = await client.pop("result_queue", timeout=5)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_pop_empty_queue_raises(self, mock_redis):
        """Test pop with empty queue name raises error."""
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient(password="test_pass")
            
            with pytest.raises(ValueError) as exc_info:
                await client.pop("", timeout=10)
            assert "Result queue name cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pop_invalid_json_raises(self, mock_redis):
        """Test pop with invalid JSON raises error."""
        mock_redis.blpop.return_value = ("result_queue", "not valid json")
        
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient(password="test_pass")
            
            with pytest.raises(json.JSONDecodeError):
                await client.pop("result_queue", timeout=10)


class TestAygaParserRedisClientQueueDepth:
    """Test suite for queue depth operations."""

    @pytest.mark.asyncio
    async def test_queue_depth(self, mock_redis):
        """Test queue depth check."""
        mock_redis.llen.return_value = 5
        
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient(password="test_pass")
            depth = await client.queue_depth("ayga_parser_redis_api")
            
            assert depth == 5
            mock_redis.llen.assert_called_once_with("ayga_parser_redis_api")

    @pytest.mark.asyncio
    async def test_queue_depth_empty_queue(self, mock_redis):
        """Test queue depth for empty queue."""
        mock_redis.llen.return_value = 0
        
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient(password="test_pass")
            depth = await client.queue_depth("empty_queue")
            
            assert depth == 0

    @pytest.mark.asyncio
    async def test_queue_depth_empty_name_raises(self, mock_redis):
        """Test queue depth with empty name raises error."""
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient(password="test_pass")
            
            with pytest.raises(ValueError) as exc_info:
                await client.queue_depth("")
            assert "Queue name cannot be empty" in str(exc_info.value)


class TestAygaParserRedisClientHealth:
    """Test suite for health check operations."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_redis):
        """Test successful health check."""
        mock_redis.ping.return_value = True
        
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient(password="test_pass")
            result = await client.health_check()
            
            assert result is True
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_redis):
        """Test failed health check."""
        import redis.asyncio as redis
        mock_redis.ping.side_effect = redis.RedisError("Connection refused")
        
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = AygaParserRedisClient(password="test_pass")
            result = await client.health_check()
            
            assert result is False
