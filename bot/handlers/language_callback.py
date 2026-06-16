"""
BlueHub Telegram Bot - Language Callback Handler
================================================
Handles inline keyboard callbacks for language selection.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select

from core.database import AsyncSessionLocal
from shared.models.user import User

logger = logging.getLogger(__name__)

router = Router(name="language_callback")


@router.callback_query(F.data.startswith("lang:"))
async def handle_language_selection(callback: CallbackQuery, T, db_user) -> None:
    """
    Handle language selection callback.

    Persists the language choice to the database user record.
    """
    locale = callback.data.split(":", 1)[1]
    if not locale:
        await callback.answer()
        return

    # Validate locale
    from bot.keyboards.language import SUPPORTED_LOCALES
    if locale not in SUPPORTED_LOCALES:
        await callback.answer(
            text="Invalid language selection.",
            show_alert=True,
        )
        return

    # Persist language preference
    success = await _save_language_preference(db_user, locale)

    if success:
        language_changed = await T("bot.language_changed", locale=locale)
        await callback.message.edit_text(
            language_changed,
        )
        await callback.answer()
        logger.info(
            "User %s changed language to %s",
            callback.from_user.id,
            locale,
        )
    else:
        error_text = await T("bot.language_error")
        await callback.answer(
            text=error_text,
            show_alert=True,
        )


@router.callback_query(F.data.startswith("lang_done:"))
async def handle_language_done(callback: CallbackQuery, T) -> None:
    """Handle language selection confirmation (Done button)."""
    await callback.message.delete()
    done_text = await T("bot.language_updated")
    await callback.message.answer(done_text)
    await callback.answer()


async def _save_language_preference(db_user, locale: str) -> bool:
    """
    Persist language preference to the database.

    Args:
        db_user: Database user object
        locale: Selected locale code

    Returns:
        bool: True if saved successfully
    """
    if db_user is None:
        return True  # Non-registered users can still use translations temporarily

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.id == db_user.id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                return False

            user.language = locale
            user.updated_at = datetime.now(timezone.utc)
            session.add(user)
            await session.commit()
            return True
    except Exception as exc:
        logger.error("Failed to save language preference: %s", exc)
        return False


__all__ = ["router"]