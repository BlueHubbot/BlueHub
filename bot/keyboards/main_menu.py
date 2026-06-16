"""
BlueHub Telegram Bot - Main Menu Keyboard
==========================================
Builds the persistent main menu reply keyboard with role-aware items.
"""
from __future__ import annotations

from typing import Any

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


async def build_main_menu(
    T: Any,
    user: Any | None = None,
    is_admin: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Build the main menu keyboard with translated labels.

    Args:
        T: Translation function
        user: Database user object (optional)
        is_admin: Whether to show admin buttons (defaults to checking user.role)

    Returns:
        ReplyKeyboardMarkup: The main menu keyboard
    """
    # Determine admin status
    if user is not None:
        role = getattr(user, "role", "customer")
        user_is_admin = role in ("admin", "superadmin")
    else:
        user_is_admin = is_admin

    builder = ReplyKeyboardBuilder()

    # Core buttons
    services_text = await T("bot.services")
    account_text = await T("bot.account")
    support_text = await T("bot.support")

    builder.row(
        KeyboardButton(text=services_text),
        KeyboardButton(text=account_text),
    )
    builder.row(
        KeyboardButton(text=support_text),
    )

    # Admin buttons (only for admin users)
    if user_is_admin:
        admin_text = await T("bot.admin")
        stats_text = await T("bot.stats")
        builder.row(
            KeyboardButton(text=admin_text),
            KeyboardButton(text=stats_text),
        )

    # Language & help
    language_text = await T("bot.language")
    help_text = await T("bot.help")
    builder.row(
        KeyboardButton(text=language_text),
        KeyboardButton(text=help_text),
    )

    return builder.as_markup(resize_keyboard=True)


__all__ = ["build_main_menu"]