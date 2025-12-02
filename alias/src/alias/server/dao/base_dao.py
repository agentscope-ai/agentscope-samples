# -*- coding: utf-8 -*-
# pylint: disable=C0301 W0622

import uuid
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from loguru import logger
from sqlmodel import SQLModel, asc, desc, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from alias.server.schemas.common import PaginationParams

ModelType = TypeVar("ModelType", bound=SQLModel)


class BaseDAO(Generic[ModelType]):
    """Base data access object providing basic CRUD operations
    for database models.

    Responsibilities:
    - Execute database operations
    - Return database model instances
    - No business logic or validation
    """

    _model_class: Type[ModelType]

    def __init__(self, session: AsyncSession):
        self.session = session
        self.model = self._model_class

    async def get(self, id: uuid.UUID) -> Optional[ModelType]:
        try:
            statement = select(self.model).where(self.model.id == id)
            result = await self.session.execute(statement)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"Error getting {self.model.__name__} with id {id}: "
                f"{str(e)}. ",
            )
            raise

    async def count_by_fields(
        self,
        filters: Dict[str, Any],
        patents: Optional[List] = None,
    ) -> int:
        try:
            query = select(func.count()).select_from(self.model)
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    query = query.where(
                        getattr(self.model, field_name) == value,
                    )
            if patents:
                for patent in patents:
                    query = query.filter(patent)
            result = await self.session.execute(query)
            return result.scalar()

        except Exception as e:
            logger.error(
                f"Error counting {self.model.__name__} with fields "
                f"{filters}: {str(e)}.",
            )
            raise

    async def get_first_by_fields(
        self,
        filters: Dict[str, Any],
    ) -> Optional[ModelType]:
        try:
            query = select(self.model)
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    query = query.where(
                        getattr(self.model, field_name) == value,
                    )
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"Error getting {self.model.__name__} by fields "
                f"{filters}: {str(e)}. ",
            )
            raise

    async def get_all_by_fields(
        self,
        filters: Dict[str, Any],
    ) -> List[ModelType]:
        try:
            query = select(self.model)
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    query = query.where(
                        getattr(self.model, field_name) == value,
                    )
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(
                f"Error getting {self.model.__name__} by fields "
                f"{filters}: {str(e)}. ",
            )
            raise

    async def get_first_by_field(
        self,
        field_name: str,
        value: Any,
    ) -> Optional[ModelType]:
        try:
            query = select(self.model).where(
                getattr(self.model, field_name) == value,
            )
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"Error getting {self.model.__name__} by {field_name}: "
                f"{str(e)}. ",
            )
            raise

    async def get_all_by_field(
        self,
        field_name: str,
        value: Any,
    ) -> List[ModelType]:
        try:
            query = select(self.model).where(
                getattr(self.model, field_name) == value,
            )
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(
                f"Error getting {self.model.__name__} by {field_name}: "
                f"{str(e)}. ",
            )
            raise

    async def delete_all_by_field(
        self,
        field_name: str,
        value: Any,
    ) -> List[ModelType]:
        try:
            query = select(self.model).where(
                getattr(self.model, field_name) == value,
            )
            result = await self.session.execute(query)
            items = result.scalars().all()
            for item in items:
                await self.session.delete(item)
            await self.session.commit()
            return items
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Error deleting {self.model.__name__} by {field_name}: "
                f"{str(e)}. ",
            )
            raise

    async def paginate(
        self,
        filters: Optional[Dict[str, Any]] = None,
        pagination: Optional[PaginationParams] = None,
        patents: Optional[List] = None,
    ) -> List[ModelType]:
        try:
            query = select(self.model)

            if filters:
                for attr, value in filters.items():
                    if hasattr(self.model, attr):
                        query = query.where(getattr(self.model, attr) == value)

            if patents:
                for patent in patents:
                    query = query.filter(patent)

            if (
                pagination
                and pagination.order_by
                and hasattr(self.model, pagination.order_by)
            ):
                order_column = getattr(self.model, pagination.order_by)
                query = query.order_by(
                    desc(order_column)
                    if pagination.order_direction == "desc"
                    else asc(order_column),
                )
            else:
                query = query.order_by(self.model.create_time.asc())

            if pagination:
                query = query.offset(pagination.skip).limit(pagination.limit)

            result = await self.session.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(
                f"Error getting multiple {self.model.__name__}: {str(e)}. ",
            )
            raise

    async def create(
        self,
        obj_data: Union[Dict[str, Any], ModelType],
    ) -> ModelType:
        try:
            for method in ["model_dump", "dict", "to_dict"]:
                if hasattr(obj_data, method):
                    obj_data = getattr(obj_data, method)()
                    break
            db_obj = self.model(**obj_data)
            self.session.add(db_obj)
            await self.session.commit()
            await self.session.refresh(db_obj)
            return db_obj
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Error creating {self.model.__name__}: {str(e)}. ",
            )
            raise

    async def update(
        self,
        id: uuid.UUID,
        obj_data: Union[Dict[str, Any], ModelType],
    ) -> ModelType:
        try:
            db_obj = await self.get(id)
            if not db_obj:
                raise ValueError(
                    f"{self.model.__name__} with id {id} not found",
                )

            for method in ["model_dump", "dict", "to_dict"]:
                if hasattr(obj_data, method):
                    obj_data = getattr(obj_data, method)()
                    break
            for field, value in obj_data.items():
                if hasattr(db_obj, field):
                    for method in ["model_dump", "dict", "to_dict"]:
                        if hasattr(value, method):
                            value = getattr(value, method)()
                            break
                    setattr(db_obj, field, value)
                else:
                    raise ValueError(
                        f"Field {field} not found in {self.model.__name__}",
                    )

            await self.session.commit()
            await self.session.refresh(db_obj)
            return db_obj
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Error updating {self.model.__name__} with id {id}: "
                f"{str(e)}. ",
            )
            raise

    async def delete(self, id: uuid.UUID) -> bool:
        try:
            db_obj = await self.get(id)
            if not db_obj:
                return False
            await self.session.delete(db_obj)
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Error deleting {self.model.__name__} with id {id}: "
                f"{str(e)}. ",
            )
            raise

    async def exists(self, id: uuid.UUID) -> bool:
        try:
            statement = select(self.model).where(self.model.id == id)
            result = await self.session.execute(statement)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(
                f"Error checking existence of {self.model.__name__} "
                f"with id {id}: {str(e)}. ",
            )
            raise
