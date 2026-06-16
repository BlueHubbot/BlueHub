"""
BlueHub Unit of Work
=====================
Transaction management with Unit of Work pattern.
Ensures atomic operations across multiple repositories.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Self

from sqlalchemy.ext.asyncio import AsyncSession

from core.database import db_manager


class UnitOfWork:
    """
    Unit of Work for managing database transactions.

    Provides atomic transaction scope with automatic commit/rollback.

    Usage:
        async with UnitOfWork() as uow:
            user_repo = UserRepository(uow.session, User)
            await user_repo.create({"name": "test"})
            # Auto-commits on success, rolls back on error
    """

    def __init__(
        self,
        session: AsyncSession | None = None,
    ) -> None:
        """
        Initialize Unit of Work.

        Args:
            session: Optional existing session. Creates new if not provided.
        """
        self._session = session
        self._external_session = session is not None

    @property
    def session(self) -> AsyncSession:
        """Get the current session."""
        if self._session is None:
            msg = "Session not initialized. Use 'async with UnitOfWork()'"
            raise RuntimeError(
                msg
            )
        return self._session

    async def __aenter__(self) -> Self:
        """Enter async context: create session."""
        if self._session is None:
            self._session = db_manager.async_session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool | None:
        """
        Exit async context: commit or rollback.

        Returns:
            None on success, suppresses exception if handled.
        """
        if self._external_session:
            # Don't manage external sessions
            return None

        try:
            if exc_type is None:
                await self._session.commit()
            else:
                await self._session.rollback()
        except Exception:
            await self._session.rollback()
            raise
        finally:
            await self._session.close()

    async def commit(self) -> None:
        """Explicitly commit the current transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Explicitly rollback the current transaction."""
        await self._session.rollback()

    async def flush(self) -> None:
        """Flush pending changes to the database."""
        await self._session.flush()

    async def execute_in_transaction(
        self,
        operations: Callable[[UnitOfWork], Any],
    ) -> Any:
        """
        Execute operations within a transaction.

        Args:
            operations: Async callable that takes a UnitOfWork instance

        Returns:
            Result of the operations callable

        Example:
            result = await uow.execute_in_transaction(async_repo_operations)
        """
        async with self:
            result = await operations(self)
            await self.commit()
            return result


__all__ = ["UnitOfWork"]
