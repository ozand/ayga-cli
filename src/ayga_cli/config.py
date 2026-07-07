"""Configuration management for ayga_parser CLI.

Implements Pydantic Settings for environment-based configuration
with OS keyring support for secure password storage.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

import keyring
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import DotEnvSettingsSource


def get_config_dir() -> Path:
    """Get platform-specific config directory.
    
    Returns:
        Path to config directory:
        - Windows: %APPDATA%\ayga-cli
        - macOS: ~/Library/Application Support/ayga-cli
        - Linux: ~/.config/ayga-cli
    """
    if sys.platform == 'win32':
        # Windows: %APPDATA%\ayga-cli
        return Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'ayga-cli'
    elif sys.platform == 'darwin':
        # macOS: ~/Library/Application Support/ayga-cli
        return Path.home() / 'Library' / 'Application Support' / 'ayga-cli'
    else:
        # Linux/Unix: ~/.config/ayga-cli
        return Path.home() / '.config' / 'ayga-cli'


CONFIG_DIR = get_config_dir()


def get_keyring_service() -> str:
    """Get platform-specific keyring service name.
    
    Returns:
        Service name for keyring:
        - Windows: Uses Windows Credential Manager
        - macOS: Uses macOS Keychain
        - Linux: Uses SecretService or KWallet
    """
    if sys.platform == 'win32':
        # Use Windows Credential Manager explicitly
        try:
            import keyring.backends.Windows
            keyring.set_keyring(keyring.backends.Windows.WinVaultKeyring())
        except Exception:
            pass
    elif sys.platform == 'darwin':
        # Use macOS Keychain
        try:
            import keyring.backends.macOS
            keyring.set_keyring(keyring.backends.macOS.Keyring())
        except Exception:
            pass
    
    return 'ayga-cli'


class AygaParserConfig(BaseSettings):
    """ayga_parser CLI configuration.

    Configuration sources (in order of priority):
    1. Environment variables (ayga_* prefix)
    2. Config file (~/.config/ayga-cli/config.yaml or .env)
    3. OS Keyring (for password)
    4. Default values

    Attributes:
        http_url: ayga_parser HTTP API endpoint.
        redis_host: Redis server hostname.
        redis_port: Redis server port.
        redis_queue: Primary Redis queue name for ayga_parser requests.
        redis_result_queue: Default queue name for results.
        redis_password: Redis authentication password (if required).
        redis_db: Redis database number.
        redis_ssl: Use SSL/TLS for Redis connection.
        password: ayga_parser API password (from keyring or env).
        default_timeout: Default request timeout in seconds.
        default_preset: Default parser preset name.
        default_config_preset: Default config preset name.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
    """

    model_config = SettingsConfigDict(
        env_prefix="ayga_",
        env_file_encoding="utf-8",
        secrets_dir="/run/secrets",  # Linux-specific, Windows/macOS use env vars
        extra="ignore",
    )

    # HTTP API Configuration
    http_url: str = Field(
        default="http://127.0.0.1:9091/API",
        description="ayga_parser HTTP API endpoint URL",
    )
    http_basic_username: str = Field(
        default="",
        description="Optional HTTP Basic Auth username",
    )
    http_basic_password: Optional[SecretStr] = Field(
        default=None,
        description="Optional HTTP Basic Auth password (defaults to API password)",
    )

    # Redis Configuration
    redis_host: str = Field(
        default="127.0.0.1",
        description="Redis server hostname",
    )
    redis_port: int = Field(
        default=6379,
        ge=1,
        le=65535,
        description="Redis server port",
    )
    redis_queue: str = Field(
        default="ayga_parser_redis_api",
        description="Primary Redis queue for ayga_parser requests",
    )
    redis_result_queue: str = Field(
        default="ayga_parser_results",
        description="Default queue name for results",
    )
    redis_password: Optional[SecretStr] = Field(
        default=None,
        description="Redis authentication password",
    )
    redis_db: int = Field(
        default=0,
        ge=0,
        description="Redis database number",
    )
    redis_ssl: bool = Field(
        default=False,
        description="Use SSL/TLS for Redis connection",
    )

    # ayga_parser Authentication
    password: Optional[SecretStr] = Field(
        default=None,
        description="ayga_parser API password (prefer keyring storage)",
    )

    # Default Settings
    default_timeout: int = Field(
        default=300,
        ge=1,
        description="Default request timeout in seconds",
    )
    default_preset: str = Field(
        default="default",
        description="Default parser preset name",
    )
    default_config_preset: str = Field(
        default="default",
        description="Default config preset name",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Load environment variables and the canonical config .env file."""
        config_dotenv = DotEnvSettingsSource(
            settings_cls,
            env_file=str(CONFIG_DIR / ".env"),
            env_file_encoding="utf-8",
        )
        return init_settings, env_settings, config_dotenv, file_secret_settings

    @field_validator("http_url")
    @classmethod
    def validate_http_url(cls, v: str) -> str:
        """Validate HTTP URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("HTTP URL must start with http:// or https://")
        return v.rstrip("/")

    def get_password(self) -> Optional[str]:
        """Get ayga_parser password from config or keyring.

        Priority:
        1. Environment variable (AYGA_PASSWORD)
        2. Config file password field
        3. OS Keyring (service: 'ayga-cli', username: 'api')

        Returns:
            The password string or None if not found.
        """
        # Check environment/config first
        if self.password:
            return self.password.get_secret_value()

        # Fall back to keyring
        try:
            pwd = keyring.get_password(get_keyring_service(), "api")
            if pwd:
                return pwd
        except Exception:
            pass

        return None

    def get_http_basic_auth(self) -> Optional[tuple[str, str]]:
        """Get HTTP Basic Auth credentials.

        Returns:
            Tuple of (username, password) if available, otherwise None.
        """
        password: Optional[str] = None
        if self.http_basic_password:
            password = self.http_basic_password.get_secret_value()
        else:
            password = self.get_password()

        if not password:
            return None

        return (self.http_basic_username, password)

    def set_password_keyring(self, password: str) -> None:
        """Store password in OS keyring.

        Args:
            password: The ayga_parser API password to store.

        Raises:
            RuntimeError: If keyring storage fails.
        """
        try:
            keyring.set_password(get_keyring_service(), "api", password)
        except Exception as e:
            raise RuntimeError(f"Failed to store password in keyring: {e}") from e

    def get_redis_url(self) -> str:
        """Build Redis connection URL.

        Returns:
            Redis URL in format redis://[:password@]host:port/db
        """
        scheme = "rediss" if self.redis_ssl else "redis"

        if self.redis_password:
            pwd = self.redis_password.get_secret_value()
            auth = f":{pwd}@"
        else:
            auth = ""

        return f"{scheme}://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @classmethod
    def get_config_dir(cls) -> Path:
        """Get the configuration directory path.

        Returns:
            Platform-specific config directory path.
        """
        return get_config_dir()

    @classmethod
    def ensure_config_dir(cls) -> Path:
        """Ensure configuration directory exists.

        Returns:
            Path to the configuration directory.
        """
        config_dir = cls.get_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir


@lru_cache(maxsize=1)
def get_config() -> AygaParserConfig:
    """Get cached configuration instance.

    Returns:
        AygaParserConfig instance with loaded settings.

    Example:
        >>> config = get_config()
        >>> print(config.redis_host)
        '127.0.0.1'
    """
    return AygaParserConfig()


def reload_config() -> AygaParserConfig:
    """Reload configuration from sources.

    Clears the cache and returns a fresh configuration instance.

    Returns:
        Fresh AygaParserConfig instance.
    """
    get_config.cache_clear()
    return get_config()
