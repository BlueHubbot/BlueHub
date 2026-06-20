"""
BlueHub Telegram Bot - Start & Help Handlers
=============================================
Handles /start and /help commands with localized welcome messages.
"""
from __future__ import annotations

import logging
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.keyboards.main_menu import build_main_menu

logger = logging.getLogger(__name__)

router = Router(name="start")


@router.message(Command("start"))
async def cmd_start(message: Message, T: Any, db_user: Any, locale: str = "en") -> None:
    """
    Handle /start command.
    Sends a localized welcome message and shows the main menu.
    """
    user_name = message.from_user.first_name or "User"

    welcome_text = await T(
        "bot.welcome",
        first_name=user_name,
    )

    # Build main menu keyboard
    keyboard = await build_main_menu(T, user=db_user)

    await message.answer(
        welcome_text,
        reply_markup=keyboard,
    )
    logger.info("User %s started the bot (locale=%s)", message.from_user.id, locale)


@router.message(Command("help"))
@router.message(F.text.lower().in_(["help", "/help"]))
async def cmd_help(message: Message, T: Any) -> None:
    """
    Handle /help command.
    Sends a localized help message describing available commands and features.
    """
    help_text = await T("bot.help")

    await message.answer(
        help_text,
        disable_web_page_preview=True,
    )


@router.message(Command("language"))
async def cmd_language(message: Message, T: Any) -> None:
    """
    Handle /language command.
    Shows current language and instructions to change it.
    """
    from bot.keyboards.language import build_language_selector

    lang_text = await T("bot.language_select")
    keyboard = await build_language_selector(T)

    await message.answer(
        lang_text,
        reply_markup=keyboard,
    )


__all__ = ["router"]
