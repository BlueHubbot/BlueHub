"""
BlueHub Telegram Bot - Admin Handlers
======================================
Admin panel access and management commands.
"""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="admin")


@router.message(Command("admin"))
async def cmd_admin(message: Message, T, db_user) -> None:
    """Admin panel entry point."""
    if db_user is None or getattr(db_user, "role", None) not in ("admin", "superadmin"):
        admin_text = await T("bot.unauthorized")
        await message.answer(admin_text)
        return

    admin_text = await T("bot.admin_welcome")
    await message.answer(admin_text)


@router.message(Command("stats"))
async def cmd_stats(message: Message, T, db_user) -> None:
    """Show system statistics to admins."""
    if db_user is None or getattr(db_user, "role", None) not in ("admin", "superadmin"):
        stats_text = await T("bot.unauthorized")
        await message.answer(stats_text)
        return

    # Placeholder - will be connected to monitoring service
    stats_text = await T("bot.stats_placeholder")
    await message.answer(stats_text)


__all__ = ["router"]