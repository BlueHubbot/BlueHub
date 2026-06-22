"""
BlueHub Telegram Bot - Authentication Middleware
================================================
Links Telegram user to database user, injects db_user into handler data.
Handles registration and sync of Telegram profile with user table.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import timezone, datetime
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TgUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session_factory as AsyncSessionLocal
from shared.models.enums import UserRole
from shared.models.user import User

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """
    Middleware that resolves the Telegram user to a BlueHub database user.

    If the user doesn't exist in the database, they are automatically registered
    with default 'user' role and 'active' status.

    Injects into handler data:
        db_user: Optional[User]  - Resolved or newly created database user
        tg_user: TgUser          - Raw Telegram user object
    """

    def setup(self, dispatcher: Any) -> None:
        """Compatibility no-op for aiogram 2.x setup pattern."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = getattr(event, "from_user", None)
        if tg_user is None:
            logger.debug("No Telegram user found in event, skipping auth")
            data["db_user"] = None
            data["tg_user"] = None
            return await handler(event, data)

        db_user = await self._resolve_user(tg_user)
        data["db_user"] = db_user
        data["tg_user"] = tg_user

        return await handler(event, data)

    async def _resolve_user(self, tg_user: TgUser) -> User | None:
        """
        Resolve Telegram user to database user, creating if necessary.

        Args:
            tg_user: Telegram user object from the update

        Returns:
            Optional[User]: Resolved database user or None on failure
        """
        async with AsyncSessionLocal() as session:
            try:
                user = await self._find_user(session, tg_user)
                if user is None:
                    user = await self._register_user(session, tg_user)
                else:
                    user = await self._sync_profile(session, user, tg_user)
                return user
            except Exception as exc:
                logger.error("Failed to resolve Telegram user %d: %s", tg_user.id, exc)
                return None

    async def _find_user(
        self, session: AsyncSession, tg_user: TgUser
    ) -> User | None:
        """Find existing user by telegram_user_id."""
        result = await session.execute(
            select(User).where(User.telegram_user_id == tg_user.id)
        )
        return result.scalar_one_or_none()

    async def _register_user(
        self, session: AsyncSession, tg_user: TgUser
    ) -> User:
        """
        Auto-register a new user from Telegram profile.

        Creates a user with:
        - telegram_user_id from tg_user.id
        - full_name from tg_user username or formatted name
        - email placeholder generated from telegram_user_id
        - language_code from tg_user.language_code
        - role: user (default)
        - is_active: True
        """
        full_name = tg_user.username or (
            f"{tg_user.first_name or ''} {tg_user.last_name or ''}".strip() or f"tg_{tg_user.id}"
        )
        email = f"tg_{tg_user.id}@telegram.bluehub.local"
        language = (tg_user.language_code or "en").split("-")[0].lower()

        user = User(
            telegram_user_id=tg_user.id,
            full_name=full_name,
            email=email,
            language_code=language,
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("Auto-registered Telegram user %d as database user %s", tg_user.id, user.id)
        return user

    async def _sync_profile(
        self, session: AsyncSession, user: User, tg_user: TgUser
    ) -> User:
        """
        Sync Telegram profile updates to the database user.

        Updates full_name and language_code if changed.
        """
        updated = False

        # Update full_name if changed
        new_full_name = tg_user.username or user.full_name
        if new_full_name and new_full_name != user.full_name:
            user.full_name = new_full_name
            updated = True

        # Update language_code if changed
        new_language = (tg_user.language_code or user.language_code or "en").split("-")[0].lower()
        if new_language != user.language_code:
            user.language_code = new_language
            updated = True

        if updated:
            user.updated_at = datetime.now(UTC)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user


__all__ = ["AuthMiddleware"]
