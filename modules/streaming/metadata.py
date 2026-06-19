"""
Streaming Module Metadata
=========================
Module definition for Streaming services (IPTV, media servers).
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
    "en": "Streaming Service",
    "fa": "سرویس استریمینگ",
}

DESCRIPTION: dict[str, str] = {
    "en": "IPTV and media streaming services including live TV, VOD, and catch-up content",
    "fa": "سرویس‌های پخش IPTV و رسانه شامل تلویزیون زنده، VOD و محتوای آرشیوی",
}

# ------------------------------------------------------------------
# Metadata
# ------------------------------------------------------------------

metadata = ModuleMetadata(
    name="streaming",
    display_name=DISPLAY_NAME,
    description=DESCRIPTION,
    version="1.0.0",
    order=40,
    default_flags=ModuleFlag(
        enabled=True,
        stop_new_sales=False,
        terminate_services=False,
        maintenance_mode=False,
    ),
    icon="live_tv",
    tags=["media", "iptv", "vod", "entertainment"],
    bot_keyboard=BotKeyboardConfig(
        text={"en": "📺 Streaming", "fa": "📺 استریمینگ"},
        description={
            "en": "IPTV channels, VOD, and media streaming services",
            "fa": "کانال‌های IPTV، VOD و سرویس‌های پخش رسانه",
        },
        row=1,
        column=2,
    ),
    admin_menu=AdminMenuConfig(
        label={"en": "Streaming Management", "fa": "مدیریت استریمینگ"},
        endpoint="/admin/streaming",
        order=40,
    ),
    default_config={
        "max_connections_per_user": 3,
        "streaming_quality_profiles": ["SD", "HD", "FHD", "4K"],
    },
)

__all__ = ["metadata"]