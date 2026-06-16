"""
BlueHub Telegram Bot - Handler Registration
============================================
Registers all bot handlers on the dispatcher.
"""
from __future__ import annotations

from aiogram import Dispatcher


def register_all_handlers(dp: Dispatcher) -> None:
    """
    Register all handler routers on the dispatcher.

    Args:
        dp: Configured aiogram Dispatcher
    """
    # Import routers
    from bot.handlers.start import router as start_router
    from bot.handlers.admin import router as admin_router
    from bot.handlers.account import router as account_router
    from bot.handlers.language_callback import router as language_router

    # Include routers
    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(account_router)
    dp.include_router(language_router)


__all__ = ["register_all_handlers"]