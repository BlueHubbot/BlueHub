"""
BlueHub Base Repository
=========================
Generic repository pattern implementation with SQLAlchemy 2.0 async support.
Provides CRUD operations with type safety and common query patterns.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, TypeVar

from sqlalchemy import Select, UnaryExpression, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import BinaryExpression

from core.exceptions import DatabaseError, NotFoundError
from core.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository[ModelT: Base]:
    """
    Generic repository providing standard CRUD operations.

    Type parameter ModelT must be a SQLAlchemy ORM model.

    Usage:
        class UserRepository(BaseRepository[User]):
            pass

        repo = UserRepository(session, User)
    """

    def __init__(
        self,
        session: AsyncSession,
        model_class: type[ModelT],
    ) -> None:
        """
        Initialize repository.

        Args:
            session: SQLAlchemy async session
            model_class: ORM model class
        """
        self._session = session
        self._model = model_class

    @property
    def model(self) -> type[ModelT]:
        """Get the model class."""
        return self._model

    @property
    def session(self) -> AsyncSession:
        """Get the current session."""
        return self._session

    # --- Query Building ---

    def _build_select(self) -> Select:
        """Build a base select statement."""
        return select(self._model)

    def _apply_ordering(
        self,
        statement: Select,
        ordering: list[UnaryExpression] | None = None,
    ) -> Select:
        """Apply ordering to a select statement."""
        if ordering:
            statement = statement.order_by(*ordering)
        return statement

    # --- Read Operations ---

    async def find_by_id(
        self,
        id: uuid.UUID | int,
        raise_if_not_found: bool = True,
    ) -> ModelT | None:
        """
        Find a record by its primary key.

        Args:
            id: Primary key value
            raise_if_not_found: If True, raises NotFoundError

        Returns:
            Model instance or None

        Raises:
            NotFoundError: If record not found and raise_if_not_found is True
        """
        try:
            result = await self._session.get(self._model, id)
            if result is None and raise_if_not_found:
                raise NotFoundError(
                    message=f"{self._model.__name__} with id={id} not found",
                    resource_type=self._model.__name__,
                    resource_id=id,
                )
            return result
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to find {self._model.__name__} by id",
                operation="find_by_id",
                details={"error": str(e)},
            ) from e

    async def find_one(
        self,
        *filters: BinaryExpression,
        ordering: list[UnaryExpression] | None = None,
        raise_if_not_found: bool = True,
    ) -> ModelT | None:
        """
        Find a single record matching the given filters.

        Args:
            *filters: SQLAlchemy filter expressions
            ordering: Optional ordering expressions
            raise_if_not_found: If True, raises NotFoundError

        Returns:
            Model instance or None
        """
        statement = self._build_select()
        if filters:
            statement = statement.where(*filters)
        statement = self._apply_ordering(statement, ordering)
        statement = statement.limit(1)

        try:
            result = await self._session.execute(statement)
            instance = result.scalars().first()
            if instance is None and raise_if_not_found:
                raise NotFoundError(
                    message=f"{self._model.__name__} not found matching criteria",
                    resource_type=self._model.__name__,
                )
            return instance
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to find {self._model.__name__}",
                operation="find_one",
                details={"error": str(e)},
            ) from e

    async def find_all(
        self,
        *filters: BinaryExpression,
        ordering: list[UnaryExpression] | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelT]:
        """
        Find all records matching the given filters with pagination.

        Args:
            *filters: SQLAlchemy filter expressions
            ordering: Optional ordering expressions
            offset: Pagination offset
            limit: Pagination limit

        Returns:
            List of model instances
        """
        statement = self._build_select()
        if filters:
            statement = statement.where(*filters)
        statement = self._apply_ordering(statement, ordering)
        statement = statement.offset(offset).limit(limit)

        try:
            result = await self._session.execute(statement)
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to find all {self._model.__name__}",
                operation="find_all",
                details={"error": str(e)},
            ) from e

    async def count(
        self,
        *filters: BinaryExpression,
    ) -> int:
        """
        Count records matching the given filters.

        Args:
            *filters: Optional filter expressions

        Returns:
            Record count
        """
        statement = select(func.count()).select_from(self._model)
        if filters:
            statement = statement.where(*filters)

        try:
            result = await self._session.execute(statement)
            return result.scalar() or 0
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to count {self._model.__name__}",
                operation="count",
                details={"error": str(e)},
            ) from e

    async def exists(
        self,
        *filters: BinaryExpression,
    ) -> bool:
        """
        Check if any record matches the given filters.

        Args:
            *filters: Filter expressions

        Returns:
            True if at least one record matches
        """
        statement = select(func.exists().where(
            select(self._model).where(*filters).exists()
        ))
        try:
            result = await self._session.execute(statement)
            return bool(result.scalar())
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to check existence of {self._model.__name__}",
                operation="exists",
                details={"error": str(e)},
            ) from e

    # --- Write Operations ---

    async def create(
        self,
        data: dict[str, Any] | ModelT,
        flush: bool = False,
    ) -> ModelT:
        """
        Create a new record.

        Args:
            data: Dictionary of field values or model instance
            flush: If True, flush to DB (don't commit)

        Returns:
            Created model instance
        """
        try:
            instance = self._model(**data) if isinstance(data, dict) else data
            self._session.add(instance)
            if flush:
                await self._session.flush()
            return instance
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create {self._model.__name__}",
                operation="create",
                details={"error": str(e)},
            ) from e

    async def update(
        self,
        id: uuid.UUID | int,
        data: dict[str, Any],
        flush: bool = False,
    ) -> ModelT:
        """
        Update a record by its primary key.

        Args:
            id: Primary key value
            data: Dictionary of field values to update
            flush: If True, flush to DB

        Returns:
            Updated model instance
        """
        try:
            instance = await self.find_by_id(id)
            for key, value in data.items():
                setattr(instance, key, value)
            if flush:
                await self.session.flush()
            return instance
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to update {self._model.__name__}",
                operation="update",
                details={"error": str(e)},
            ) from e

    async def update_many(
        self,
        filters: list[BinaryExpression],
        data: dict[str, Any],
    ) -> int:
        """
        Update multiple records matching filters.

        Args:
            filters: Filter expressions
            data: Dictionary of field values to update

        Returns:
            Number of records updated
        """
        statement = (
            update(self._model)
            .where(*filters)
            .values(**data)
            .execution_mode(synchronize_session="fetch")
        )
        try:
            result = await self._session.execute(statement)
            return result.rowcount
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to update many {self._model.__name__}",
                operation="update_many",
                details={"error": str(e)},
            ) from e

    async def delete(
        self,
        id: uuid.UUID | int,
        soft_delete: bool = True,
    ) -> None:
        """
        Delete a record by its primary key.

        Args:
            id: Primary key value
            soft_delete: If True, marks as deleted instead of removing
        """
        try:
            instance = await self.find_by_id(id)
            if soft_delete and hasattr(instance, "soft_delete"):
                instance.soft_delete()
            else:
                await self._session.delete(instance)
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to delete {self._model.__name__}",
                operation="delete",
                details={"error": str(e)},
            ) from e

    async def delete_many(
        self,
        filters: list[BinaryExpression],
        soft_delete: bool = True,
    ) -> int:
        """
        Delete multiple records matching filters.

        Args:
            filters: Filter expressions
            soft_delete: If True, marks as deleted

        Returns:
            Number of records affected
        """
        try:
            if soft_delete and hasattr(self._model, "is_deleted"):
                return await self.update_many(
                    filters,
                    {"is_deleted": True, "deleted_at": func.now()},
                )
            statement = delete(self._model).where(*filters)
            result = await self._session.execute(statement)
            return result.rowcount
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to delete many {self._model.__name__}",
                operation="delete_many",
                details={"error": str(e)},
            ) from e

    # --- Bulk Operations ---

    async def bulk_create(
        self,
        items: list[dict[str, Any]],
    ) -> list[ModelT]:
        """
        Create multiple records in bulk.

        Args:
            items: List of dictionaries with field values

        Returns:
            List of created model instances
        """
        try:
            instances = [self._model(**item) for item in items]
            self._session.add_all(instances)
            return instances
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to bulk create {self._model.__name__}",
                operation="bulk_create",
                details={"error": str(e)},
            ) from e


__all__ = ["BaseRepository"]
