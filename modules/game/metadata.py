"""
Game Module Metadata
====================
Module definition for Game hosting services (game servers, voice servers).
"""

from __future__ import annotations

from core.registry.schemas import (
    AdminMenuConfig,
    BotKeyboardConfig,
    ModuleFlag,
    ModuleMetadata,
)

# ------------------------------------------------------------------
# Translations (Persian / English)
# ------------------------------------------------------------------
DISPLAY_NAME: dict[str, str] = {
    "en": "Game Service",
    "fa": "سرویس گیم",
}

DESCRIPTION: dict[str, str] = {
    "en": "Game server hosting services including Minecraft, Valheim, and voice server hosting",
    "fa": "سرویس‌های میزبانی سرور بازی شامل Minecraft، Valheim و میزبانی سرور صوتی",
}

# ------------------------------------------------------------------
# Metadata
# ------------------------------------------------------------------

metadata = ModuleMetadata(
    name="game",
    display_name=DISPLAY_NAME,
    description=DESCRIPTION,
    version="1.0.0",
    order=50,
    default_flags=ModuleFlag(
        enabled=True,
        stop_new_sales=False,
        terminate_services=False,
        maintenance_mode=False,
    ),
    icon="sports_esports",
    tags=["gaming", "hosting", "voice"],
    bot_keyboard=BotKeyboardConfig(
        text={"en": "🎮 Game", "fa": "🎮 گیم"},
        description={
            "en": "Game servers, voice servers, and hosting services",
            "fa": "سرورهای بازی، سرورهای صوتی و سرویس‌های میزبانی",
        },
        row=2,
        column=0,
    ),
    admin_menu=AdminMenuConfig(
        label={"en": "Game Management", "fa": "مدیریت گیم"},
        endpoint="/admin/game",
        order=50,
    ),
    default_config={
        "max_servers_per_user": 3,
        "auto_backup_enabled": True,
        "backup_interval_hours": 24,
    },
)

__all__ = ["metadata"]
