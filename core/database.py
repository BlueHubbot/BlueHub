
"""
BlueHub Database Module
=========================
PostgreSQL session management with SQLAlchemy 2.0 async support.
Provides engine, session factory, and lifecycle management.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from core.config import settings


def build_db_url(is_async: bool = True) -> str:
    """
    Build database URL suitable for async or sync usage.

    Args:
        is_async: If True, use async driver (asyncpg). If False, use sync (psycopg2).

    Returns:
        Database connection string.
    """
    url = str(settings.DATABASE_URL)
    if is_async:
        return url
    # Convert async URL to sync for Alembic/SQLAlchemy sync usage
    return url.replace("+asyncpg", "+psycopg2")


class DatabaseManager:
    """
    Manages database engine and session lifecycle.
    Supports both sync and async operations.
    """

    def __init__(self, db_url: str | None = None) -> None:
        self._db_url = db_url or build_db_url(is_async=True)
        self._async_engine: AsyncEngine | None = None
        self._sync_engine = None
        self._async_session_factory: async_sessionmaker[AsyncSession] | None = (
            None
        )
        self._sync_session_factory: sessionmaker[Session] | None = None

    # --- Async Engine ---

    @property
    def async_engine(self) -> AsyncEngine:
        """Get or create the async SQLAlchemy engine."""
        if self._async_engine is None:
            self._async_engine = create_async_engine(
                url=self._db_url,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                echo=settings.DATABASE_ECHO,
                pool_pre_ping=True,
            )
        return self._async_engine

    @property
    def async_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get or create the async session factory."""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
        return self._async_session_factory

    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Provide an async session for dependency injection.
        Usage: async with db_manager.get_async_session() as session:
        """
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @asynccontextmanager
    async def async_session_context(self) -> AsyncIterator[AsyncSession]:
        """
        Context manager for async session.
        Usage: async with db_manager.async_session_context() as session:
        """
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    # --- Sync Engine ---

    @property
    def sync_engine(self):
        """Get or create the sync SQLAlchemy engine."""
        if self._sync_engine is None:
            sync_url = build_db_url(is_async=False)
            self._sync_engine = create_engine(
                url=sync_url,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                echo=settings.DATABASE_ECHO,
                pool_pre_ping=True,
            )
        return self._sync_engine

    @property
    def sync_session_factory(self) -> sessionmaker[Session]:
        """Get or create the sync session factory."""
        if self._sync_session_factory is None:
            self._sync_session_factory = sessionmaker(
                bind=self.sync_engine,
                class_=Session,
                expire_on_commit=False,
                autoflush=False,
            )
        return self._sync_session_factory

    def get_sync_session(self) -> Session:
        """Get a sync session (for scripts, alembic migrations)."""
        session = self.sync_session_factory()
        try:
            return session
        except Exception:
            session.close()
            raise

    # --- Lifecycle ---

    async def close(self) -> None:
        """Dispose of all engines and connections."""
        if self._async_engine is not None:
            await self._async_engine.dispose()
            self._async_engine = None
            self._async_session_factory = None
        if self._sync_engine is not None:
            self._sync_engine.dispose()
            self._sync_engine = None
            self._sync_session_factory = None

    async def check_connection(self) -> bool:
        """Check if database connection is alive."""
        try:
            async with self.async_engine.connect() as conn:
                await conn.execute(
                    __import__("sqlalchemy").text("SELECT 1")
                )
            return True
        except Exception:
            return False


# Global database manager instance
db_manager = DatabaseManager()


class _LazySessionFactoryProxy:
    """
    Lazy proxy that defers engine creation to first use.

    Module-level imports of ``async_session_factory`` will not trigger
    SQLAlchemy engine creation.  Only the first ``async with
    async_session_factory() as db:`` call materialises the engine.
    """

    _factory: async_sessionmaker[AsyncSession] | None = None

    def __call__(self) -> AsyncSession:
        if self._factory is None:
            self._factory = db_manager.async_session_factory
        return self._factory()


async_session_factory = _LazySessionFactoryProxy()

__all__ = [
    "DatabaseManager",
    "async_session_factory",
    "build_db_url",
    "db_manager",
]
