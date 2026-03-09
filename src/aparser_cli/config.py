"""Configuration management for A-Parser CLI.

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


def get_config_dir() -> Path:
    """Get platform-specific config directory.
    
    Returns:
        Path to config directory:
        - Windows: %APPDATA%\aparser-cli
        - macOS: ~/Library/Application Support/aparser-cli
        - Linux: ~/.config/aparser-cli
    """
    if sys.platform == 'win32':
        # Windows: %APPDATA%\aparser-cli
        return Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'aparser-cli'
    elif sys.platform == 'darwin':
        # macOS: ~/Library/Application Support/aparser-cli
        return Path.home() / 'Library' / 'Application Support' / 'aparser-cli'
    else:
        # Linux/Unix: ~/.config/aparser-cli
        return Path.home() / '.config' / 'aparser-cli'


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
    
    return 'aparser-cli'


class AParserConfig(BaseSettings):
    """A-Parser CLI configuration.

    Configuration sources (in order of priority):
    1. Environment variables (APARSER_* prefix)
    2. Config file (~/.config/aparser-cli/config.yaml or .env)
    3. OS Keyring (for password)
    4. Default values

    Attributes:
        http_url: A-Parser HTTP API endpoint.
        redis_host: Redis server hostname.
        redis_port: Redis server port.
        redis_queue: Primary Redis queue name for A-Parser requests.
        redis_result_queue: Default queue name for results.
        redis_password: Redis authentication password (if required).
        redis_db: Redis database number.
        redis_ssl: Use SSL/TLS for Redis connection.
        password: A-Parser API password (from keyring or env).
        default_timeout: Default request timeout in seconds.
        default_preset: Default parser preset name.
        default_config_preset: Default config preset name.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
    """

    model_config = SettingsConfigDict(
        env_prefix="APARSER_",
        env_file=str(get_config_dir() / '.env'),
        env_file_encoding="utf-8",
        yaml_file=str(get_config_dir() / 'config.yaml'),
        secrets_dir="/run/secrets",  # Linux-specific, Windows/macOS use env vars
        extra="ignore",
    )

    # HTTP API Configuration
    http_url: str = Field(
        default="http://127.0.0.1:9091/API",
        description="A-Parser HTTP API endpoint URL",
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
        default="aparser_redis_api",
        description="Primary Redis queue for A-Parser requests",
    )
    redis_result_queue: str = Field(
        default="aparser_results",
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

    # A-Parser Authentication
    password: Optional[SecretStr] = Field(
        default=None,
        description="A-Parser API password (prefer keyring storage)",
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

    @field_validator("http_url")
    @classmethod
    def validate_http_url(cls, v: str) -> str:
        """Validate HTTP URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("HTTP URL must start with http:// or https://")
        return v.rstrip("/")

    def get_password(self) -> Optional[str]:
        """Get A-Parser password from config or keyring.

        Priority:
        1. Environment variable (APARSER_PASSWORD)
        2. Config file password field
        3. OS Keyring (service: 'aparser-cli', username: 'api')

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

    def set_password_keyring(self, password: str) -> None:
        """Store password in OS keyring.

        Args:
            password: The A-Parser API password to store.

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
            Path to ~/.config/aparser-cli/
        """
        config_dir = Path.home() / ".config" / "aparser-cli"
        return config_dir

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
def get_config() -> AParserConfig:
    """Get cached configuration instance.

    Returns:
        AParserConfig instance with loaded settings.

    Example:
        >>> config = get_config()
        >>> print(config.redis_host)
        '127.0.0.1'
    """
    return AParserConfig()


def reload_config() -> AParserConfig:
    """Reload configuration from sources.

    Clears the cache and returns a fresh configuration instance.

    Returns:
        Fresh AParserConfig instance.
    """
    get_config.cache_clear()
    return get_config()
