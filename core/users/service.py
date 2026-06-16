"""
BlueHub User Service
=====================
Service layer for user CRUD operations, profile management,
and password management.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.password import hash_password, verify_password
from core.users.schemas import UserCreate, UserUpdate
from shared.models.enums import UserRole
from shared.models.user import User


class UserNotFoundError(Exception):
    """Raised when a user is not found."""


class DuplicateEmailError(Exception):
    """Raised when attempting to create a user with an existing email."""


class InvalidPasswordError(Exception):
    """Raised when current password verification fails."""


class UserService:
    """Service for managing platform users."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user(self, data: UserCreate) -> User:
        """
        Create a new user.

        Args:
            data: User creation data including email and password.

        Returns:
            The newly created User instance.

        Raises:
            DuplicateEmailError: If the email already exists.
        """
        # Check for duplicate email
        existing = await self.get_by_email(data.email)
        if existing:
            msg = f"User with email '{data.email}' already exists"
            raise DuplicateEmailError(msg)

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            language_code=data.language_code,
            telegram_user_id=data.telegram_user_id,
            role=UserRole.USER,
            is_active=True,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def get_by_id(self, user_id: str) -> User | None:
        """
        Get a user by their UUID.

        Args:
            user_id: The UUID string of the user.

        Returns:
            The User instance if found, None otherwise.
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """
        Get a user by their email address.

        Args:
            email: The email address to look up.

        Returns:
            The User instance if found, None otherwise.
        """
        stmt = select(User).where(User.email == email.lower().strip())
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """
        Get a user by their Telegram user ID.

        Args:
            telegram_id: The Telegram user ID.

        Returns:
            The User instance if found, None otherwise.
        """
        stmt = select(User).where(User.telegram_user_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def update_user(self, user_id: str, data: UserUpdate) -> User:
        """
        Update a user's profile information.

        Args:
            user_id: The UUID of the user to update.
            data: The fields to update.

        Returns:
            The updated User instance.

        Raises:
            UserNotFoundError: If the user is not found.
        """
        user = await self.get_by_id(user_id)
        if not user:
            msg = f"User with id '{user_id}' not found"
            raise UserNotFoundError(msg)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def delete_user(self, user_id: str) -> None:
        """
        Soft-delete a user by setting them inactive.

        Args:
            user_id: The UUID of the user to delete.

        Raises:
            UserNotFoundError: If the user is not found.
        """
        user = await self.get_by_id(user_id)
        if not user:
            msg = f"User with id '{user_id}' not found"
            raise UserNotFoundError(msg)

        user.is_active = False
        await self.session.flush()

    async def hard_delete_user(self, user_id: str) -> None:
        """
        Permanently delete a user from the database.

        Args:
            user_id: The UUID of the user to permanently delete.

        Raises:
            UserNotFoundError: If the user is not found.
        """
        user = await self.get_by_id(user_id)
        if not user:
            msg = f"User with id '{user_id}' not found"
            raise UserNotFoundError(msg)

        await self.session.delete(user)
        await self.session.flush()

    async def update_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> User:
        """
        Update a user's password after verifying the current one.

        Args:
            user_id: The UUID of the user.
            current_password: The user's current password for verification.
            new_password: The new password to set.

        Returns:
            The updated User instance.

        Raises:
            UserNotFoundError: If the user is not found.
            InvalidPasswordError: If the current password is incorrect.
        """
        user = await self.get_by_id(user_id)
        if not user:
            msg = f"User with id '{user_id}' not found"
            raise UserNotFoundError(msg)

        if not verify_password(current_password, user.password_hash):
            msg = "Current password is incorrect"
            raise InvalidPasswordError(msg)

        user.password_hash = hash_password(new_password)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        role: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        """
        List users with pagination and optional filters.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            role: Optional role filter.
            is_active: Optional active status filter.
            search: Optional search string for email or name.

        Returns:
            A tuple of (list of User instances, total count).
        """
        query = select(User)
        count_query = select(func.count(User.id))

        # Apply filters
        if role:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)

        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                User.email.ilike(search_pattern) | User.full_name.ilike(search_pattern)
            )
            count_query = count_query.where(
                User.email.ilike(search_pattern) | User.full_name.ilike(search_pattern)
            )

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)

        result = await self.session.execute(query)
        users = list(result.unique().scalars().all())

        return users, total

    async def count_active_users(self) -> int:
        """Get the count of active users."""
        stmt = select(func.count(User.id)).where(User.is_active)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def update_preferences(
        self, user_id: str, language_code: str
    ) -> User:
        """
        Update user preferences (language, etc.).

        Args:
            user_id: The UUID of the user.
            language_code: The new language code.

        Returns:
            The updated User instance.

        Raises:
            UserNotFoundError: If the user is not found.
        """
        user = await self.get_by_id(user_id)
        if not user:
            msg = f"User with id '{user_id}' not found"
            raise UserNotFoundError(msg)

        user.language_code = language_code
        await self.session.flush()
        await self.session.refresh(user)
        return user


__all__ = [
    "DuplicateEmailError",
    "InvalidPasswordError",
    "UserNotFoundError",
    "UserService",
]
