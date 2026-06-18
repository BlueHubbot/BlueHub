"""
BlueHub Telegram Bot - i18n Middleware
======================================
Detects user language and provides translation function T() via handler data.
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict

try:
    from aiogram import BaseMiddleware
    from aiogram.types import TelegramObject, User as TgUser
except ImportError:
    BaseMiddleware = object  # type: ignore[assignment,misc]
    TelegramObject = object  # type: ignore[assignment,misc]
    TgUser = object  # type: ignore[assignment,misc]

from core.i18n.engine import I18nEngine

logger = logging.getLogger(__name__)

# Singleton i18n engine
_i18n = I18nEngine(default_locale="en", cache_ttl=3600)


class I18nMiddleware(BaseMiddleware):
    """
    Middleware that detects user language and injects a translation helper.

    Injects into handler data:
        T(key, **kwargs) -> str  : Translation function
        locale: str               : Detected locale code

    Language detection priority:
        1. User's language_code from Telegram profile
        2. Default locale (en)
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Determine locale from Telegram user
        locale = self._detect_locale(event)

        # Load translations for this locale
        await _i18n._ensure_loaded(locale)

        # Create translation helper
        async def T(key: str, **kwargs: Any) -> str:
            return await _i18n.get(key, locale=locale, **kwargs)

        # Inject into handler data
        data["T"] = T
        data["locale"] = locale

        return await handler(event, data)

    def _detect_locale(self, event: TelegramObject) -> str:
        """Extract locale from Telegram event user."""
        tg_user: TgUser | None = getattr(event, "from_user", None)
        if tg_user and tg_user.language_code:
            lang = tg_user.language_code
            # Normalize: use first 2 chars (e.g., 'en-US' -> 'en')
            normalized = lang.split("-")[0].lower()
            # Map Telegram codes to our supported locales
            # Telegram uses IETF BCP 47, we use ISO 639-1
            supported = _i18n._loaded if hasattr(_i18n, "_loaded") else {"en", "fa", "ar", "tr", "ru", "de", "fr", "es"}
            if normalized in supported:
                return normalized
            logger.debug("Unsupported locale '%s', falling back to 'en'", lang)

        return "en"


__all__ = ["I18nMiddleware"]