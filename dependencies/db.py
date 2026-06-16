"""
BlueHub Database Dependencies
=============================
FastAPI dependency injection for database sessions.
Provides `get_async_session` for use with `Depends()` in route handlers.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from core.database import db_manager


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    Usage:
        @router.get("/example")
        async def example_endpoint(
            session: AsyncSession = Depends(get_async_session),
        ):
            ...

    Yields:
        AsyncSession: SQLAlchemy async session with automatic commit/rollback.
    """
    async with db_manager.async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


__all__ = ["get_async_session"]
