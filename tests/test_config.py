"""Tests for ayga_parser CLI configuration."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from pydantic import ValidationError

from ayga_cli.config import AygaParserConfig, get_config, get_config_dir, reload_config


class TestAygaParserConfig:
    """Test suite for AygaParserConfig."""
    import sys

    def test_default_values(self):
        """Test default configuration values."""
        config = AygaParserConfig()
        assert config.http_url == "http://127.0.0.1:9091/API"
        assert config.redis_host == "127.0.0.1"
        assert config.redis_port == 6379
        assert config.redis_queue == "ayga_parser_redis_api"
        assert config.redis_result_queue == "ayga_parser_results"
        assert config.redis_db == 0
        assert config.redis_ssl is False
        assert config.default_timeout == 300
        assert config.default_preset == "default"
        assert config.default_config_preset == "default"
        assert config.log_level == "INFO"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = AygaParserConfig(
            http_url="https://example.com:8080/API",
            redis_host="redis.example.com",
            redis_port=6380,
            redis_queue="custom_queue",
            default_timeout=600,
        )
        assert config.http_url == "https://example.com:8080/API"
        assert config.redis_host == "redis.example.com"
        assert config.redis_port == 6380
        assert config.redis_queue == "custom_queue"
        assert config.default_timeout == 600

    def test_http_url_validation(self):
        """Test HTTP URL validation."""
        # Valid URLs
        config = AygaParserConfig(http_url="http://localhost:9091/API")
        assert config.http_url == "http://localhost:9091/API"
        
        config = AygaParserConfig(http_url="https://example.com/API/")
        assert config.http_url == "https://example.com/API"

    def test_http_url_validation_invalid(self):
        """Test HTTP URL validation with invalid URL."""
        with pytest.raises(ValidationError) as exc_info:
            AygaParserConfig(http_url="ftp://invalid.com")
        assert "HTTP URL must start with http:// or https://" in str(exc_info.value)

    def test_redis_port_validation(self):
        """Test Redis port validation."""
        # Valid port
        config = AygaParserConfig(redis_port=1)
        assert config.redis_port == 1
        
        config = AygaParserConfig(redis_port=65535)
        assert config.redis_port == 65535

    def test_redis_port_validation_invalid(self):
        """Test Redis port validation with invalid ports."""
        with pytest.raises(ValidationError):
            AygaParserConfig(redis_port=0)
        
        with pytest.raises(ValidationError):
            AygaParserConfig(redis_port=65536)

    def test_log_level_validation(self):
        """Test log level validation."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            config = AygaParserConfig(log_level=level)
            assert config.log_level == level

    def test_log_level_validation_invalid(self):
        """Test log level validation with invalid level."""
        with pytest.raises(ValidationError):
            AygaParserConfig(log_level="INVALID")

    def test_get_password_from_config(self):
        """Test getting password from config."""
        from pydantic import SecretStr
        config = AygaParserConfig(password=SecretStr("my_secret"))
        assert config.get_password() == "my_secret"

    def test_get_password_from_keyring(self):
        """Test getting password from keyring fallback."""
        with patch("ayga_cli.config.keyring.get_password") as mock_get:
            mock_get.return_value = "keyring_password"
            config = AygaParserConfig()
            assert config.get_password() == "keyring_password"
            mock_get.assert_called_once_with("ayga-cli", "api")

    def test_get_password_not_found(self):
        """Test getting password when not configured."""
        with patch("ayga_cli.config.keyring.get_password") as mock_get:
            mock_get.return_value = None
            config = AygaParserConfig()
            assert config.get_password() is None

    def test_set_password_keyring(self):
        """Test storing password in keyring."""
        with patch("ayga_cli.config.keyring.set_password") as mock_set:
            config = AygaParserConfig()
            config.set_password_keyring("new_password")
            mock_set.assert_called_once_with("ayga-cli", "api", "new_password")

    def test_set_password_keyring_failure(self):
        """Test keyring storage failure."""
        with patch("ayga_cli.config.keyring.set_password") as mock_set:
            mock_set.side_effect = Exception("Keyring error")
            config = AygaParserConfig()
            with pytest.raises(RuntimeError) as exc_info:
                config.set_password_keyring("new_password")
            assert "Failed to store password in keyring" in str(exc_info.value)

    def test_get_redis_url_no_auth(self):
        """Test Redis URL generation without auth."""
        config = AygaParserConfig(
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
        )
        assert config.get_redis_url() == "redis://localhost:6379/0"

    def test_get_redis_url_with_auth(self):
        """Test Redis URL generation with auth."""
        from pydantic import SecretStr
        config = AygaParserConfig(
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
            redis_password=SecretStr("secret123"),
        )
        assert config.get_redis_url() == "redis://:secret123@localhost:6379/0"

    def test_get_redis_url_ssl(self):
        """Test Redis URL generation with SSL."""
        config = AygaParserConfig(
            redis_host="localhost",
            redis_port=6380,
            redis_ssl=True,
        )
        assert config.get_redis_url() == "rediss://localhost:6380/0"

    def test_get_config_dir(self):
        """Test getting config directory."""
        config_dir = AygaParserConfig.get_config_dir()
        assert isinstance(config_dir, Path)
        assert config_dir.name == "ayga-cli"
        assert config_dir == get_config_dir()
        import sys
        if sys.platform == "win32":
            assert config_dir.parent.name == "Roaming"
        elif sys.platform == "darwin":
            assert config_dir.parent.name == "Application Support"
        else:
            assert config_dir.parent.name == ".config"

    def test_get_config_dir_windows(self, monkeypatch):
        """Test Windows config directory resolution."""
        appdata = Path("C:/Users/test/AppData/Roaming")
        monkeypatch.setenv("APPDATA", str(appdata))
        with patch("ayga_cli.config.sys.platform", "win32"):
            config_dir = get_config_dir()
        assert config_dir == appdata / "ayga-cli"

    def test_get_config_dir_macos(self):
        """Test macOS config directory resolution."""
        with patch("ayga_cli.config.sys.platform", "darwin"):
            with patch("ayga_cli.config.Path.home", return_value=Path("/Users/test")):
                config_dir = get_config_dir()
        assert config_dir == Path("/Users/test/Library/Application Support/ayga-cli")

    def test_get_config_dir_linux(self):
        """Test Linux config directory resolution."""
        with patch("ayga_cli.config.sys.platform", "linux"):
            with patch("ayga_cli.config.Path.home", return_value=Path("/home/test")):
                config_dir = get_config_dir()
        assert config_dir == Path("/home/test/.config/ayga-cli")

    def test_ensure_config_dir(self):
        """Test ensuring config directory exists."""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            config_dir = AygaParserConfig.ensure_config_dir()
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
            assert isinstance(config_dir, Path)


class TestConfigCache:
    """Test suite for config caching."""

    def test_get_config_caching(self):
        """Test that get_config returns cached instance."""
        # Clear cache first
        reload_config()
        
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_reload_config_clears_cache(self):
        """Test that reload_config clears the cache."""
        config1 = get_config()
        config2 = reload_config()
        assert config1 is not config2
