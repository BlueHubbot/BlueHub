"""
BlueHub Telegram Bot - Language Selector Keyboard
==================================================
Inline keyboard for selecting the bot language.
"""
from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Supported locales with display names (displayed in their own language)
SUPPORTED_LOCALES = {
    "en": "🇬🇧 English",
    "fa": "🇮🇷 فارسی",
    "ar": "🇸🇦 العربية",
    "tr": "🇹🇷 Türkçe",
    "ru": "🇷🇺 Русский",
    "de": "🇩🇪 Deutsch",
    "fr": "🇫🇷 Français",
    "es": "🇪🇸 Español",
}


async def build_language_selector(T: Any) -> InlineKeyboardMarkup:
    """
    Build inline keyboard for language selection.

    Each button triggers a callback to change the user's language preference.

    Args:
        T: Translation function

    Returns:
        InlineKeyboardMarkup: Language selector keyboard
    """
    builder = InlineKeyboardBuilder()

    for locale_code, locale_name in SUPPORTED_LOCALES.items():
        builder.button(
            text=locale_name,
            callback_data=f"lang:{locale_code}",
        )

    # Arrange in 2 columns
    builder.adjust(2)

    return builder.as_markup()


async def build_language_confirmation(T: Any, locale: str) -> InlineKeyboardMarkup:
    """
    Build a simple confirmation keyboard after language change.

    Args:
        T: Translation function
        locale: Selected locale code

    Returns:
        InlineKeyboardMarkup: Confirmation keyboard with "Done" button
    """
    builder = InlineKeyboardBuilder()
    done_text = await T("bot.language_done")
    builder.button(
        text=done_text,
        callback_data=f"lang_done:{locale}",
    )
    return builder.as_markup()


__all__ = [
    "build_language_selector",
    "build_language_confirmation",
    "SUPPORTED_LOCALES",
]
