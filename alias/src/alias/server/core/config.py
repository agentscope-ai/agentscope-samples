# -*- coding: utf-8 -*-
# mypy: disable-error-code="misc"
# pylint: disable=line-too-long

import os
import secrets
from typing import Any, Literal, Optional, Union

from pydantic import (
    computed_field,
    Field,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file(max_levels=3):
    """Find environment configuration file,
    supports searching up multiple directory levels"""
    for env_file in [".env", ".env.example"]:
        current_path = os.getcwd()
        levels_checked = 0
        while levels_checked <= max_levels:
            potential_path = os.path.join(current_path, env_file)
            if os.path.isfile(potential_path):
                return potential_path
            # Move up one directory level
            new_path = os.path.dirname(current_path)
            # If we've reached the root directory, break
            if new_path == current_path:
                break
            current_path = new_path
            levels_checked += 1

    # If we exit the loop without having found the file
    raise FileNotFoundError(
        f".env file not found within {max_levels} levels of {os.getcwd()}.",
    )


def parse_cors(v: Any) -> Union[list[str], str]:
    """Parse CORS configuration,
    supports comma-separated string or list format"""
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, (list, str)):
        return v
    raise ValueError(v)


# =============================================================================
# 1. CORE SYSTEM CONFIGURATION (Critical - Must be configured)
# =============================================================================


class ApplicationConfig(BaseSettings):
    """Application basic configuration - Core system identity"""

    PROJECT_NAME: str = Field(default="Alias", description="Project name")
    VERSION: str = Field(default="0.2.0", description="Project version")
    ENVIRONMENT: Literal["local", "dev", "staging", "production"] = Field(
        default="local",
        description="Runtime environment",
    )


class SecurityConfig(BaseSettings):
    """Security configuration - Critical for authentication and API security"""

    API_V1_STR: str = Field(
        default="/api/v1",
        description="API version prefix",
    )
    INNER_API_KEY: Optional[str] = Field(
        default=None,
        description="Internal API key",
    )
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="JWT secret key",
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60 * 24 * 8,
        description="Access token expire time (minutes)",
    )


class ServerConfig(BaseSettings):
    """Server configuration - Core server settings"""

    BACKEND_URL: Optional[str] = Field(
        default="http://localhost:8000",
        description="Backend URL",
    )
    USER_PROFILING_BASE_URL: Optional[str] = Field(
        default=None,
        description="User profiling service URL",
    )
    ENABLE_BACKGROUND_CHAT: bool = Field(
        default=False,
        description="Whether to enable background chat",
    )
    MAX_CHAT_EXECUTION_TIME: int = Field(
        default=60 * 60,
        description="Maximum chat execution time (seconds)",
    )
    HEARTBEAT_INTERVAL: int = Field(
        default=10,
        description="Heartbeat interval (seconds)",
    )


class DatabaseConfig(BaseSettings):
    """Database connection configuration - Essential for data persistence"""

    DB_HOST: str = Field(
        default="localhost",
        description="Database host address",
    )
    DB_PORT: int = Field(default=5432, description="Database port")
    DB_USER: str = Field(default="alias", description="Database username")
    DB_PASSWORD: str = Field(default="alias", description="Database password")
    DB_NAME: str = Field(default="alias", description="Database name")
    USE_POSTGRESQL: Optional[bool] = Field(
        default=False,
        description="Whether to use PostgreSQL",
    )

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Build database connection URI"""
        if self.USE_POSTGRESQL:
            return (
                f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@"
                f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
        return f"sqlite:///alias-{getattr(self, 'ENVIRONMENT', 'local')}.db"


class UserConfig(BaseSettings):
    """User configuration - Initial superuser setup"""

    FIRST_SUPERUSER_EMAIL: str = Field(
        default="alias@agentscope.com",
        description="First superuser",
    )
    FIRST_SUPERUSER_USERNAME: str = Field(
        default="alias",
        description="First superuser",
    )
    FIRST_SUPERUSER_PASSWORD: str = Field(
        default="alias",
        description="First superuser password",
    )


class StorageConfig(BaseSettings):
    """Storage configuration - File storage settings"""

    STORAGE_TYPE: Literal["local", "oss"] = Field(
        default="local",
        description="Storage type",
    )
    LOCAL_STORAGE_DIR: str = Field(
        default="~/.alias/local_storage",
        description="Local storage directory",
    )


# =============================================================================
# 2. CORE FEATURES CONFIGURATION (Essential - Required for main functionality)
# =============================================================================


class RedisConfig(BaseSettings):
    """Redis cache configuration -
    Essential for caching and session management"""

    REDIS_HOST: str = Field(
        default="localhost",
        description="Redis host address",
    )
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_USERNAME: Optional[str] = Field(
        default=None,
        description="Redis username",
    )
    REDIS_PASSWORD: Optional[str] = Field(
        default=None,
        description="Redis password",
    )


class SandboxConfig(BaseSettings):
    """Sandbox configuration - Core sandbox functionality"""

    SANDBOX_PORT: Optional[int] = Field(
        default=8001,
        description="Sandbox port",
    )
    SANDBOX_TYPE: Optional[str] = Field(
        default="alias",
        description="Sandbox type",
    )
    SANDBOX_URL: Optional[str] = Field(
        default=None,
        description="Sandbox endpoint",
    )
    SANDBOX_BEARER_TOKEN: Optional[str] = Field(
        default=None,
        description="Sandbox bearer token",
    )
    SANDBOX_PUBLIC_HOST: Optional[str] = Field(
        default="localhost",
        description="Sandbox public host",
    )


# =============================================================================
# 3. FEATURE-SPECIFIC CONFIGURATION
# (Important - Required for specific features)
# =============================================================================


class LoggingConfig(BaseSettings):
    """Logging configuration - Application logging"""

    LOG_FILE: str = Field(
        default="./logs/app.log",
        description="Log file path",
    )
    LOG_FORMAT: Optional[str] = Field(default=None, description="Log format")
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    LOG_ROTATION: str = Field(
        default="500 MB",
        description="Log rotation size",
    )
    LOG_RETENTION: str = Field(default="10", description="Log retention days")


# =============================================================================
# 4. ADVANCED CONFIGURATION (Optional - Performance tuning and monitoring)
# =============================================================================


class DatabasePoolConfig(BaseSettings):
    """Database connection pool configuration - Performance tuning"""

    DB_POOL_SIZE: int = Field(default=30, description="Connection pool size")
    DB_MAX_OVERFLOW: int = Field(
        default=30,
        description="Maximum overflow connections",
    )
    DB_POOL_TIMEOUT: int = Field(
        default=30,
        description="Connection pool timeout (seconds)",
    )
    DB_POOL_RECYCLE: int = Field(
        default=3600,
        description="Connection recycle time (seconds)",
    )
    DB_POOL_PRE_PING: bool = Field(
        default=True,
        description="Ping before connection",
    )
    DB_ECHO: bool = Field(
        default=False,
        description="Whether to print SQL statements",
    )

    @computed_field
    @property
    def DB_CONNECTION_ARGS(self) -> dict:
        """Database connection arguments"""
        return {
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_MAX_OVERFLOW,
            "pool_timeout": self.DB_POOL_TIMEOUT,
            "pool_pre_ping": self.DB_POOL_PRE_PING,
            "pool_recycle": self.DB_POOL_RECYCLE,
            "echo": self.DB_ECHO,
        }


class OssConfig(BaseSettings):
    """Alibaba Cloud OSS configuration - Cloud storage"""

    OSS_ENDPOINT: Optional[str] = Field(
        default=None,
        description="OSS endpoint",
    )
    OSS_ACCESS_KEY_ID: Optional[str] = Field(
        default=None,
        description="OSS access key ID",
    )
    OSS_ACCESS_KEY_SECRET: Optional[str] = Field(
        default=None,
        description="OSS access key secret",
    )
    OSS_BUCKET_NAME: Optional[str] = Field(
        default=None,
        description="OSS bucket name",
    )


# =============================================================================
# Main Configuration Class
# =============================================================================


# pylint: disable=too-many-ancestors
class Settings(
    ApplicationConfig,
    DatabaseConfig,
    DatabasePoolConfig,
    RedisConfig,
    StorageConfig,
    OssConfig,
    SecurityConfig,
    LoggingConfig,
    ServerConfig,
    SandboxConfig,
    UserConfig,
):
    """Main configuration class, integrates all configurations"""

    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_ignore_empty=True,
        extra="ignore",
    )

    def model_post_init(self, _) -> None:
        """Post initialization configuration

        Args:
            context: Validation context from Pydantic (unused)
        """

        if (
            self.SANDBOX_URL is None
            and self.SANDBOX_PUBLIC_HOST
            and self.SANDBOX_PORT
        ):
            self.SANDBOX_URL = (
                f"http://{self.SANDBOX_PUBLIC_HOST}:{self.SANDBOX_PORT}"
            )


settings = Settings()  # type: ignore
