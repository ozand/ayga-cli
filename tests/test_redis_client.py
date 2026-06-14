"""Tests for ayga-parser Redis client."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from ayga_cli.client.redis import ayga-parserRedisClient


class Testayga-parserRedisClient:
    """Test suite for ayga-parserRedisClient."""

    def test_init_default_values(self):
        """Test client initialization with default values."""
        client = ayga-parserRedisClient(password="test_pass")
        assert client.redis_host == "127.0.0.1"
        assert client.redis_port == 6379
        assert client.redis_queue == "ayga-parser_redis_api"
        assert client.redis_password is None
        assert client.password == "test_pass"
        assert client._redis is None

    def test_init_custom_values(self):
        """Test client initialization with custom values."""
        client = ayga-parserRedisClient(
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
            
            client = ayga-parserRedisClient(password="test")
            redis_instance = await client._get_redis()
            
            assert redis_instance is not None
            assert client._redis is not None
            MockRedis.assert_called_once_with(
                host="127.0.0.1",
                port=6379,
                password=None,
                decode_responses=True,
            )

    @pytest.mark.asyncio
    async def test_get_redis_reuse_connection(self):
        """Test that Redis connection is reused."""
        with patch("redis.asyncio.Redis") as MockRedis:
            mock_redis = AsyncMock()
            MockRedis.return_value = mock_redis
            
            client = ayga-parserRedisClient(password="test")
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
            
            client = ayga-parserRedisClient(password="test")
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
            
            async with ayga-parserRedisClient(password="test") as client:
                assert client is not None
                # Trigger connection creation so close() will be called
                await client._get_redis()
            
            # Redis client uses close() for async close
            mock_redis.close.assert_called_once()


class Testayga-parserRedisClientPush:
    """Test suite for Redis push operations."""

    @pytest.mark.asyncio
    async def test_push_success(self, mock_redis):
        """Test successful Redis LPUSH."""
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = ayga-parserRedisClient(password="test_pass")
            result_queue = await client.push(
                parser="SE::Google",
                query="test query",
                preset="default",
            )
            
            assert result_queue.startswith("ayga-parser_results_")
            mock_redis.lpush.assert_called_once()
            
            # Verify the pushed data
            call_args = mock_redis.lpush.call_args
            assert call_args[0][0] == "ayga-parser_redis_api"  # queue name
            # Second arg is JSON string
            pushed_data = json.loads(call_args[0][1])
            assert pushed_data["password"] == "test_pass"
            assert pushed_data["action"] == "oneRequest"
            assert pushed_data["data"]["parser"] == "SE::Google"
            assert pushed_data["data"]["query"] == "test query"

    @pytest.mark.asyncio
    async def test_push_with_custom_result_queue(self, mock_redis):
        """Test push with custom result queue."""
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = ayga-parserRedisClient(password="test_pass")
            result_queue = await client.push(
                parser="SE::Google",
                query="test",
                result_queue="my_custom_queue",
            )
            
            assert result_queue == "my_custom_queue"
            pushed_data = json.loads(mock_redis.lpush.call_args[0][1])
            assert pushed_data["data"]["resultQueue"] == "my_custom_queue"

    @pytest.mark.asyncio
    async def test_push_with_options(self, mock_redis):
        """Test push with options."""
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = ayga-parserRedisClient(password="test_pass")
            options = [{"id": "pagecount", "value": 5}]
            
            await client.push(
                parser="SE::Google",
                query="test",
                options=options,
            )
            
            pushed_data = json.loads(mock_redis.lpush.call_args[0][1])
            assert pushed_data["data"]["options"] == options

    @pytest.mark.asyncio
    async def test_push_empty_parser_raises(self, mock_redis):
        """Test push with empty parser raises error."""
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = ayga-parserRedisClient(password="test_pass")
            
            with pytest.raises(ValueError) as exc_info:
                await client.push(parser="", query="test")
            assert "Parser name cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_push_empty_query_raises(self, mock_redis):
        """Test push with empty query raises error."""
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = ayga-parserRedisClient(password="test_pass")
            
            with pytest.raises(ValueError) as exc_info:
                await client.push(parser="SE::Google", query="")
            assert "Query cannot be empty" in str(exc_info.value)


class Testayga-parserRedisClientPop:
    """Test suite for Redis pop operations."""

    @pytest.mark.asyncio
    async def test_pop_success(self, mock_redis):
        """Test successful Redis BLPOP."""
        mock_redis.blpop.return_value = (
            "result_queue",
            json.dumps({"success": 1, "data": {"resultString": "test result"}}),
        )
        
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = ayga-parserRedisClient(password="test_pass")
            result = await client.pop("result_queue", timeout=10)
            
            assert result["success"] == 1
            assert result["data"]["resultString"] == "test result"
            mock_redis.blpop.assert_called_once_with("result_queue", timeout=10)

    @pytest.mark.asyncio
    async def test_pop_timeout(self, mock_redis):
        """Test pop with timeout (no result)."""
        mock_redis.blpop.return_value = None
        
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = ayga-parserRedisClient(password="test_pass")
            result = await client.pop("result_queue", timeout=5)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_pop_empty_queue_raises(self, mock_redis):
        """Test pop with empty queue name raises error."""
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = ayga-parserRedisClient(password="test_pass")
            
            with pytest.raises(ValueError) as exc_info:
                await client.pop("", timeout=10)
            assert "Result queue name cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pop_invalid_json_raises(self, mock_redis):
        """Test pop with invalid JSON raises error."""
        mock_redis.blpop.return_value = ("result_queue", "not valid json")
        
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = ayga-parserRedisClient(password="test_pass")
            
            with pytest.raises(json.JSONDecodeError):
                await client.pop("result_queue", timeout=10)


class Testayga-parserRedisClientQueueDepth:
    """Test suite for queue depth operations."""

    @pytest.mark.asyncio
    async def test_queue_depth(self, mock_redis):
        """Test queue depth check."""
        mock_redis.llen.return_value = 5
        
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = ayga-parserRedisClient(password="test_pass")
            depth = await client.queue_depth("ayga-parser_redis_api")
            
            assert depth == 5
            mock_redis.llen.assert_called_once_with("ayga-parser_redis_api")

    @pytest.mark.asyncio
    async def test_queue_depth_empty_queue(self, mock_redis):
        """Test queue depth for empty queue."""
        mock_redis.llen.return_value = 0
        
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = ayga-parserRedisClient(password="test_pass")
            depth = await client.queue_depth("empty_queue")
            
            assert depth == 0

    @pytest.mark.asyncio
    async def test_queue_depth_empty_name_raises(self, mock_redis):
        """Test queue depth with empty name raises error."""
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = ayga-parserRedisClient(password="test_pass")
            
            with pytest.raises(ValueError) as exc_info:
                await client.queue_depth("")
            assert "Queue name cannot be empty" in str(exc_info.value)


class Testayga-parserRedisClientHealth:
    """Test suite for health check operations."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_redis):
        """Test successful health check."""
        mock_redis.ping.return_value = True
        
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = ayga-parserRedisClient(password="test_pass")
            result = await client.health_check()
            
            assert result is True
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_redis):
        """Test failed health check."""
        import redis.asyncio as redis
        mock_redis.ping.side_effect = redis.RedisError("Connection refused")
        
        with patch("redis.asyncio.Redis", return_value=mock_redis):
            client = ayga-parserRedisClient(password="test_pass")
            result = await client.health_check()
            
            assert result is False
