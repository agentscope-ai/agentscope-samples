# -*- coding: utf-8 -*-
"""
Redis configuration for user profiling service
"""
import os


class UserProfilingRedisConfig:
    """Redis configuration for user profiling service"""

    def __init__(self):
        # Redis connection settings
        self.REDIS_HOST = os.getenv("USER_PROFILING_REDIS_HOST", "localhost")
        self.REDIS_PORT = int(os.getenv("USER_PROFILING_REDIS_PORT", "6379"))
        self.REDIS_DB = int(
            os.getenv("USER_PROFILING_REDIS_DB", "1"),
        )  # Use DB 1 for user profiling
        self.REDIS_PASSWORD = os.getenv("USER_PROFILING_REDIS_PASSWORD", None)

        # Task expiration settings
        self.TASK_EXPIRY_HOURS = int(
            os.getenv("USER_PROFILING_TASK_EXPIRY_HOURS", "24"),
        )
        self.CLEANUP_MAX_AGE_HOURS = int(
            os.getenv("USER_PROFILING_CLEANUP_MAX_AGE_HOURS", "24"),
        )

        # Key prefixes
        self.KEY_PREFIX = "user_profiling"

    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        if self.REDIS_PASSWORD:
            return (
                f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:"
                f"{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        else:
            return (
                f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            )

    def get_task_expiry_seconds(self) -> int:
        """Get task expiry time in seconds"""
        return self.TASK_EXPIRY_HOURS * 60 * 60


# Global configuration instance
redis_config = UserProfilingRedisConfig()
