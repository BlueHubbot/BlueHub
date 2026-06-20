from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from bot.main import create_bot, create_dispatcher
except ImportError as e:
    logger.warning("aiogram not installed; bot functions unavailable: %s", e)

    def create_bot(*args: object, **kwargs: object) -> None:  # type: ignore[no-redef]
        """Stub: aiogram is not installed."""
        raise ImportError(
            "aiogram is required for bot functionality. "
            "Install with: pip install aiogram"
        )

    def create_dispatcher(*args: object, **kwargs: object) -> None:  # type: ignore[no-redef]
        """Stub: aiogram is not installed."""
        raise ImportError(
            "aiogram is required for bot functionality. "
            "Install with: pip install aiogram"
        )

__all__ = ["create_bot", "create_dispatcher"]
