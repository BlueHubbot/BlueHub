"""
BlueHub Telegram Bot - SmartDNS Handlers
=========================================
Admin-focused SmartDNS profile and DNS record management.
"""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from core.database import async_session_factory
from modules.smartdns.services import SmartDnsService

logger = logging.getLogger(__name__)

router = Router(name="smartdns")


@router.message(Command("smartdns"))
async def cmd_smartdns(message: Message, T, db_user) -> None:
    """SmartDNS admin panel entry point."""
    if db_user is None or getattr(db_user, "role", None) not in ("admin", "superadmin"):
        admin_text = await T("bot.unauthorized")
        await message.answer(admin_text)
        return

    welcome = await T("smartdns.admin_welcome")
    help_text = (
        f"{welcome}\n\n"
        "/smartdns_list - لیست پروفایل‌ها\n"
        "/smartdns_health - وضعیت سلامت\n"
        "/smartdns_sync_all - همگام‌سازی همه"
    )
    await message.answer(help_text)


@router.message(Command("smartdns_list"))
async def cmd_smartdns_list(message: Message, T, db_user) -> None:
    """List all SmartDNS profiles."""
    if db_user is None or getattr(db_user, "role", None) not in ("admin", "superadmin"):
        admin_text = await T("bot.unauthorized")
        await message.answer(admin_text)
        return

    async with async_session_factory() as db:
        service = SmartDnsService(db)
        profiles = await service.list_profiles(limit=50)

        if not profiles:
            await message.answer("📭 هیچ پروفایل SmartDNS یافت نشد.")
            return

        lines = ["📋 **پروفایل‌های SmartDNS:**\n"]
        for p in profiles:
            status_emoji = {"active": "🟢", "suspended": "🔴", "error": "⚠️"}.get(
                p.status, "⚪"
            )
            lines.append(
                f"{status_emoji} `{p.profile_name}` [{p.status}] - {p.geo_region or 'N/A'}"
            )

        await message.answer("\n".join(lines))


@router.message(Command("smartdns_health"))
async def cmd_smartdns_health(message: Message, T, db_user) -> None:
    """Check SmartDNS profiles health status."""
    if db_user is None or getattr(db_user, "role", None) not in ("admin", "superadmin"):
        admin_text = await T("bot.unauthorized")
        await message.answer(admin_text)
        return

    async with async_session_factory() as db:
        service = SmartDnsService(db)
        profiles = await service.list_profiles(limit=500)

        healthy = 0
        errors = 0
        for profile in profiles:
            try:
                status_info = await service.get_profile_status(profile.id)
                if status_info.status == "error":
                    errors += 1
                else:
                    healthy += 1
            except Exception:
                errors += 1

    await message.answer(
        f"🏥 **وضعیت سلامت SmartDNS:**\n\n"
        f"✅ سالم: {healthy}\n"
        f"⚠️ خطا: {errors}\n"
        f"📊 مجموع: {len(profiles)}"
    )


@router.message(Command("smartdns_sync_all"))
async def cmd_smartdns_sync_all(message: Message, T, db_user) -> None:
    """Sync all SmartDNS profiles with PowerDNS."""
    if db_user is None or getattr(db_user, "role", None) not in ("admin", "superadmin"):
        admin_text = await T("bot.unauthorized")
        await message.answer(admin_text)
        return

    await message.answer("🔄 در حال همگام‌سازی همه پروفایل‌ها...")

    async with async_session_factory() as db:
        service = SmartDnsService(db)
        profiles = await service.list_profiles(status="active", limit=100)

        synced_total = 0
        failed_total = 0

        for p in profiles:
            try:
                result = await service.sync_records(p.id)
                synced_total += result.synced
                failed_total += result.failed
            except Exception as exc:
                logger.error("Error syncing profile %s: %s", p.id, exc)
                failed_total += 1

    await message.answer(
        f"🔄 **نتیجه همگام‌سازی:**\n\n"
        f"✅ همگام‌سازی شده: {synced_total}\n"
        f"❌ ناموفق: {failed_total}"
    )


__all__ = ["router"]