# -*- coding: utf-8 -*-
"""The database related services"""
# pylint: disable=redefined-outer-name
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from sqlmodel.ext.asyncio.session import AsyncSession

from alias.server.services.database_service import DatabaseService


database_service = DatabaseService()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with database_service.get_session() as session:
        yield session


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Get database session as async context manager"""
    async with database_service.get_session() as session:
        yield session


async def initialize_database() -> None:
    """Get database session"""
    await database_service.init_database()
    await database_service.upgrade()
    await database_service.create_superuser()


async def close_database() -> None:
    """Close database session"""
    await database_service.dispose()
