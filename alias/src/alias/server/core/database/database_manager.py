# -*- coding: utf-8 -*-

from typing import AsyncGenerator

from contextlib import asynccontextmanager
from loguru import logger

from sqlmodel import text, SQLModel
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool


class DatabaseManager:
    def __init__(self, db_uri: str, connection_args: dict = None) -> None:
        self.db_uri = self._convert_db_uri(db_uri)

        default_connection_args = {
            "pool_size": 30,
            "max_overflow": 30,
            "pool_timeout": 30,
            "pool_recycle": 1800,
            "echo": False,
        }
        connection_args = connection_args or default_connection_args
        self.pool_size = connection_args.get("pool_size", 30)
        self.max_overflow = connection_args.get("max_overflow", 30)
        self.pool_timeout = connection_args.get("pool_timeout", 30)
        self.echo = connection_args.get("echo", False)
        self.pool_recycle = connection_args.get("pool_recycle", 1800)

        self._engine = self._create_engine()

        self._session_maker = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
        )

    def _convert_db_uri(self, uri: str) -> str:
        """Convert database URI to async version"""
        if uri.startswith("postgresql://"):
            return uri.replace("postgresql://", "postgresql+asyncpg://")
        elif uri.startswith("sqlite://"):
            return uri.replace("sqlite://", "sqlite+aiosqlite://")
        return uri

    def _create_engine(self) -> AsyncEngine:
        """Create SQLAlchemy async engine"""
        try:
            if self.db_uri.startswith("postgresql+asyncpg://"):
                engine = create_async_engine(
                    self.db_uri,
                    poolclass=AsyncAdaptedQueuePool,
                    pool_size=self.pool_size,
                    max_overflow=self.max_overflow,
                    pool_timeout=self.pool_timeout,
                    pool_recycle=self.pool_recycle,
                    pool_pre_ping=True,
                    echo=self.echo,
                )
                logger.info("Created PostgreSQL engine with connection pool")
                return engine

            elif self.db_uri.startswith("sqlite+aiosqlite://"):
                connect_args = {"check_same_thread": False}
                engine = create_async_engine(
                    self.db_uri,
                    connect_args=connect_args,
                    echo=self.echo,
                )
                logger.info("Created SQLite engine")
                return engine

            else:
                raise ValueError(f"Unsupported database type: {self.db_uri}")
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise

    @property
    def engine(self) -> AsyncEngine:
        """Get database engine instance"""
        if not self._engine:
            raise RuntimeError(
                "Database not initialized. Call initialize() first.",
            )
        return self._engine

    async def dispose(self) -> None:
        """Dispose database engine"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_maker = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session as async context manager"""

        async with self._session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e
            finally:
                await session.close()

    async def check_connection(self) -> bool:
        """Check database connection"""
        try:
            async with self.session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False

    async def create_tables(self) -> None:
        """Create all tables"""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            logger.info("Tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    async def drop_tables(self) -> None:
        """Drop all tables"""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.drop_all)
            logger.info("Tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
