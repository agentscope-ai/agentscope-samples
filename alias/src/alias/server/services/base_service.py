# -*- coding: utf-8 -*-
# pylint: disable=C0301 W0622
import traceback
import uuid
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel

from alias.server.cache.base_cache import BaseCache
from alias.server.dao.base_dao import BaseDAO
from alias.server.schemas.common import PaginationParams

ModelType = TypeVar("ModelType", bound=SQLModel)


class BaseService(Generic[ModelType]):
    _model_cls: Type[ModelType]
    _dao_cls: Type[BaseDAO[ModelType]]
    _cache_cls: Optional[Type[BaseCache[ModelType]]] = None

    def __init__(self, session: AsyncSession):
        self.dao = self._dao_cls(session=session)
        self.cache = (
            self._cache_cls()  # pylint: disable=E1102
            if self._cache_cls
            else None
        )
        self.session = session

    # cache methods
    async def set_cache(
        self,
        key: Union[str, uuid.UUID],
        value: ModelType,
    ) -> bool:
        return await self.cache.set_cache(key, value) if self.cache else True

    async def get_cache(
        self,
        key: Union[str, uuid.UUID],
    ) -> Optional[ModelType]:
        return await self.cache.get_cache(key) if self.cache else None

    async def clear_cache(self, key: Union[str, uuid.UUID]) -> None:
        if self.cache:
            await self.cache.clear_cache(key)

    # dao methods
    async def get(self, id: uuid.UUID) -> Optional[ModelType]:
        try:
            cached_item = await self.get_cache(id)
            if cached_item:
                return cached_item
            item = await self.dao.get(id)
            if item:
                await self.set_cache(id, item)
            return item
        except Exception as e:
            logger.error(
                f"Service error getting entity with id {id}: {str(e)}, "
                f"\n traceback: {traceback.format_exc()}",
            )
            raise

    async def create(
        self,
        obj_in: Union[Dict[str, Any], ModelType],
    ) -> ModelType:
        try:
            item = await self.dao.create(obj_in)
            await self.set_cache(item.id, item)
            return item
        except Exception as e:
            logger.error(
                f"Service error creating entity: {obj_in}, error: {str(e)}, "
                f"\n traceback: {traceback.format_exc()}",
            )
            raise

    async def update(
        self,
        id: uuid.UUID,
        obj_in: Union[Dict[str, Any], ModelType],
    ) -> ModelType:
        try:
            await self._validate_update(id, obj_in)
            item = await self.dao.update(
                id,
                obj_in,
            )
            await self.set_cache(id, item)
            return item
        except Exception as e:
            logger.error(
                f"Service error updating entity with id {id}: {str(e)}, "
                f"\n traceback: {traceback.format_exc()}",
            )
            raise

    async def delete(self, id: uuid.UUID) -> bool:
        try:
            await self._validate_delete(id)
            result = await self.dao.delete(id)
            if result:
                await self.clear_cache(id)
            return result
        except Exception as e:
            logger.error(
                f"Service error deleting entity with id {id}: {str(e)}, "
                f"\n traceback: {traceback.format_exc()}",
            )
            raise

    async def count_by_fields(
        self,
        filters: Dict[str, Any],
        patents: Optional[List] = None,
    ) -> int:
        try:
            return await self.dao.count_by_fields(
                filters=filters,
                patents=patents,
            )
        except Exception as e:
            logger.error(
                f"Service error counting entities by {filters}: {str(e)}, "
                f"\n traceback: {traceback.format_exc()}",
            )
            raise

    async def paginate(
        self,
        filters: Optional[Dict[str, Any]] = None,
        pagination: Optional[PaginationParams] = None,
        patents: Optional[List] = None,
    ) -> List[ModelType]:
        try:
            return await self.dao.paginate(
                filters=filters,
                pagination=pagination,
                patents=patents,
            )
        except Exception as e:
            logger.error(
                f"Service error getting multiple entities: {str(e)}, "
                f"\n traceback: {traceback.format_exc()}",
            )
            raise

    async def get_last_by_fields(
        self,
        filters: Dict[str, Any],
    ) -> Optional[ModelType]:
        try:
            items = await self.dao.get_all_by_fields(filters)
            if len(items) > 0:
                return items[-1]
            return None
        except Exception as e:
            logger.error(
                f"Service error getting last entity by fields {filters}: "
                f"{str(e)}, \n traceback: {traceback.format_exc()}",
            )
            raise

    async def get_all_by_fields(
        self,
        filters: Dict[str, Any],
    ) -> List[ModelType]:
        try:
            return await self.dao.get_all_by_fields(filters)
        except Exception as e:
            logger.error(
                f"Service error getting entities by fields {filters}: "
                f"{str(e)}, \n traceback: {traceback.format_exc()}",
            )
            raise

    async def get_first_by_field(
        self,
        field_name: str,
        value: Any,
    ) -> Optional[ModelType]:
        try:
            return await self.dao.get_first_by_field(field_name, value)
        except Exception as e:
            logger.error(
                f"Service error getting entity by {field_name}: {str(e)}, "
                f"\n traceback: {traceback.format_exc()}",
            )
            raise

    async def get_last_by_field(
        self,
        field_name: str,
        value: Any,
    ) -> Optional[ModelType]:
        try:
            values = await self.dao.get_all_by_field(field_name, value)
            if len(values) > 0:
                return values[-1]
            return None
        except Exception as e:
            logger.error(
                f"Service error getting last entity by {field_name}: "
                f"{str(e)}, \n traceback: {traceback.format_exc()}",
            )
            raise

    async def get_all_by_field(
        self,
        field_name: str,
        value: Any,
    ) -> List[ModelType]:
        try:
            return await self.dao.get_all_by_field(field_name, value)
        except Exception as e:
            logger.error(
                f"Service error getting entities by {field_name}: "
                f"{str(e)}, \n traceback: {traceback.format_exc()}",
            )
            raise

    async def delete_all_by_field(
        self,
        field_name: str,
        value: Any,
    ) -> List[ModelType]:
        try:
            return await self.dao.delete_all_by_field(field_name, value)
        except Exception as e:
            logger.error(
                f"Service error deleting entities by {field_name}: "
                f"{str(e)}, \n traceback: {traceback.format_exc()}",
            )
            raise

    async def _validate_create(
        self,
        obj_in: Union[Dict[str, Any], ModelType],
    ) -> None:
        pass

    async def _validate_update(
        self,
        instance_id: uuid.UUID,
        obj_in: Union[Dict[str, Any], ModelType],
    ) -> None:
        pass

    async def _validate_delete(self, instance_id: uuid.UUID) -> None:
        pass

    async def _validate_exists(self, instance_id: uuid.UUID) -> None:
        pass
