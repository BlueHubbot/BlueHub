"""
BlueHub Telegram Bot - Authentication Middleware
================================================
Links Telegram user to database user, injects db_user into handler data.
Handles registration and sync of Telegram profile with user table.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal
from shared.models.user import User
from shared.models.enums import UserRole, UserStatus

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """
    Middleware that resolves the Telegram user to a BlueHub database user.

    If the user doesn't exist in the database, they are automatically registered
    with default 'customer' role and 'active' status.

    Injects into handler data:
        db_user: Optional[User]  - Resolved or newly created database user
        tg_user: TgUser          - Raw Telegram user object
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user: Optional[TgUser] = getattr(event, "from_user", None)
        if tg_user is None:
            logger.debug("No Telegram user found in event, skipping auth")
            data["db_user"] = None
            data["tg_user"] = None
            return await handler(event, data)

        db_user = await self._resolve_user(tg_user)
        data["db_user"] = db_user
        data["tg_user"] = tg_user

        return await handler(event, data)

    async def _resolve_user(self, tg_user: TgUser) -> Optional[User]:
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
    ) -> Optional[User]:
        """Find existing user by telegram_id."""
        result = await session.execute(
            select(User).where(User.telegram_id == str(tg_user.id))
        )
        return result.scalar_one_or_none()

    async def _register_user(
        self, session: AsyncSession, tg_user: TgUser
    ) -> User:
        """
        Auto-register a new user from Telegram profile.

        Creates a user with:
        - telegram_id from tg_user.id
        - username from tg_user.username or formatted name
        - email placeholder generated from telegram_id
        - language from tg_user.language_code
        - role: customer (default)
        - status: active
        """
        username = tg_user.username or (
            f"{tg_user.first_name or ''} {tg_user.last_name or ''}".strip() or f"tg_{tg_user.id}"
        )
        email = f"tg_{tg_user.id}@telegram.bluehub.local"
        language = (tg_user.language_code or "en").split("-")[0].lower()

        user = User(
            telegram_id=str(tg_user.id),
            username=username,
            email=email,
            language=language,
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
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

        Updates username and language if changed.
        """
        updated = False

        # Update username if changed
        new_username = tg_user.username or user.username
        if new_username and new_username != user.username:
            user.username = new_username
            updated = True

        # Update language if changed
        new_language = (tg_user.language_code or user.language or "en").split("-")[0].lower()
        if new_language != user.language:
            user.language = new_language
            updated = True

        if updated:
            user.updated_at = datetime.now(timezone.utc)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user


__all__ = ["AuthMiddleware"]