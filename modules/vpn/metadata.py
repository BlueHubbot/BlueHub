"""
VPN Module Metadata
===================
Module definition for VPN services (WireGuard, VLESS+REALITY, etc.).
Provides display names in Persian and English, bot keyboard configuration,
admin menu configuration, and default module flags.
"""

from __future__ import annotations

from typing import Dict

from core.registry.schemas import ModuleFlag, ModuleMetadata

# ------------------------------------------------------------------
# Translations (Persian / English)
# ------------------------------------------------------------------
DISPLAY_NAME: Dict[str, str] = {
    "en": "VPN Service",
    "fa": "سرویس VPN",
}

DESCRIPTION: Dict[str, str] = {
    "en": "Secure VPN services with WireGuard & VLESS+REALITY protocols",
    "fa": "سرویس‌های امن VPN با پروتکل‌های WireGuard و VLESS+REALITY",
}

BOT_KEYBOARD_TEXT: Dict[str, str] = {
    "en": "🛡 VPN",
    "fa": "🛡 وی‌پی‌ان",
}

BOT_KEYBOARD_DESCRIPTION: Dict[str, str] = {
    "en": "Manage your VPN services, view usage, and download configs",
    "fa": "مدیریت سرویس‌های VPN، مشاهده مصرف و دانلود کانفیگ",
}

ADMIN_MENU_LABEL: Dict[str, str] = {
    "en": "VPN Management",
    "fa": "مدیریت VPN",
}

# ------------------------------------------------------------------
# Metadata
# ------------------------------------------------------------------

metadata = ModuleMetadata(
    name="vpn",
    display_name=DISPLAY_NAME,
    description=DESCRIPTION,
    version="1.0.0",
    order=10,
    default_flags=ModuleFlag(
        enabled=True,
        stop_new_sales=False,
        terminate_services=False,
        maintenance_mode=False,
    ),
    icon="shield_lock",
    tags=["network", "security", "tunnel", "vpn"],
    bot_keyboard={
        "text": BOT_KEYBOARD_TEXT,
        "description": BOT_KEYBOARD_DESCRIPTION,
        "row": 1,
        "column": 1,
    },
    admin_menu={
        "label": ADMIN_MENU_LABEL,
        "endpoint": "/admin/vpn",
        "order": 10,
    },
    default_config={
        "max_accounts_per_user": 5,
        "traffic_poll_interval_seconds": 300,
        "connection_sync_interval_seconds": 120,
        "peer_renew_days_before_expiry": 7,
    },
)

__all__ = ["metadata", "DISPLAY_NAME", "DESCRIPTION"]