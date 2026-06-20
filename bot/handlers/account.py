"""
BlueHub Telegram Bot - Account Handler
========================================
Handles account-related functionality and profile viewing.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="account")


@router.message(Command("account"))
@router.message(F.text.lower().in_(["account", "/account"]))
async def cmd_account(message: Message, T, db_user) -> None:
    """Show user account information."""
    if db_user is None:
        not_found = await T("bot.account_not_found")
        await message.answer(not_found)
        return

    account_text = await T(
        "bot.account_info",
        username=db_user.username or "N/A",
        email=db_user.email or "N/A",
        role=getattr(db_user, "role", "customer"),
        language=db_user.language or "en",
    )
    await message.answer(account_text)


__all__ = ["router"]
