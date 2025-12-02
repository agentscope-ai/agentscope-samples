# -*- coding: utf-8 -*-
import uuid
from datetime import timedelta
from typing import Any, Generic, Optional, Type, TypeVar, Union

from sqlmodel import SQLModel

from alias.server.core.cache import Cache

ModelType = TypeVar("ModelType", bound=SQLModel)


class BaseCache(Generic[ModelType]):
    _model_cls: Type[ModelType]
    _cache_prefix: Optional[str] = None
    _cache_expire: Optional[Union[int, timedelta]] = None

    def __init__(self, redis_cache: Optional[Cache] = None):
        self.cache = redis_cache or Cache()
        if not self._cache_prefix:
            self._cache_prefix = self._model_cls.__name__.lower()

    def _get_cache_key(self, *args: Any) -> str:
        return f"{self._cache_prefix}:" + ":".join(str(arg) for arg in args)

    async def set_cache(
        self,
        key: Union[str, uuid.UUID],
        value: ModelType,
    ) -> bool:
        cache_key = self._get_cache_key(key)
        return await self.cache.set(cache_key, value, ex=self._cache_expire)

    async def get_cache(
        self,
        key: Union[str, uuid.UUID],
    ) -> Optional[ModelType]:
        cache_key = self._get_cache_key(key)
        cache_data = await self.cache.get(cache_key)
        if cache_data:
            return self._model_cls.model_validate(cache_data)
        return None

    async def clear_cache(self, key: Union[str, uuid.UUID]) -> None:
        cache_key = self._get_cache_key(key)
        await self.cache.delete(cache_key)
