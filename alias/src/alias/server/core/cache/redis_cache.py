# -*- coding: utf-8 -*-
import traceback
from datetime import timedelta
from typing import Any, Optional, Union

from loguru import logger

from alias.server.core.serializer import JsonSerializer
from alias.server.utils.redis import redis_client


class RedisCache:
    """Async Redis cache wrapper with serialization and basic operations."""

    def __init__(
        self,
    ) -> None:
        self.serializer = JsonSerializer()

    async def set(
        self,
        key: str,
        value: Any,
        ex: Optional[Union[int, timedelta]] = None,
    ) -> bool:
        try:
            if isinstance(ex, timedelta):
                ex = int(ex.total_seconds())

            serialized_data = self.serializer.serialize(value)
            return bool(await redis_client.set(key, serialized_data, ex=ex))
        except Exception as e:
            logger.error(
                f"Redis set error: {str(e)}\n{traceback.format_exc()}",
            )
            return False

    async def get(self, key: str) -> Any:
        try:
            data = await redis_client.get(key)
            if data is None:
                return None
            return self.serializer.deserialize(data)
        except Exception as e:
            logger.error(
                f"Redis get error: {str(e)}\n{traceback.format_exc()}",
            )
            return None

    async def delete(self, *keys: str) -> int:
        try:
            return await redis_client.delete(*keys)
        except Exception as e:
            logger.error(
                f"Redis delete error: {str(e)}\n{traceback.format_exc()}",
            )
            return 0

    async def exists(self, key: str) -> bool:
        try:
            return bool(await redis_client.exists(key))
        except Exception as e:
            logger.error(
                f"Redis exists error: {str(e)}\n{traceback.format_exc()}",
            )
            return False

    async def expire(self, key: str, time: Union[int, timedelta]) -> bool:
        try:
            if isinstance(time, timedelta):
                time = int(time.total_seconds())
            return bool(await redis_client.expire(key, time))
        except Exception as e:
            logger.error(f"Redis expire error: {str(e)}")
            return False

    async def ttl(self, key: str) -> int:
        try:
            return await redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Redis ttl error: {str(e)}")
            return -2

    async def close(self) -> None:
        """Close Redis connection."""
        try:
            await redis_client.close()
        except Exception as e:
            logger.error(f"Error closing Redis connection: {str(e)}")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
