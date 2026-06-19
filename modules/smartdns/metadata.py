"""
SmartDNS Module Metadata
========================
Module definition for SmartDNS services.
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
    "en": "SmartDNS Service",
    "fa": "سرویس SmartDNS",
}

DESCRIPTION: dict[str, str] = {
    "en": "Smart DNS proxy services for bypassing geo-restrictions and DNS-based content filtering",
    "fa": "سرویس‌های پروکسی DNS هوشمند برای عبور از محدودیت‌های جغرافیایی",
}

# ------------------------------------------------------------------
# Metadata
# ------------------------------------------------------------------

metadata = ModuleMetadata(
    name="smartdns",
    display_name=DISPLAY_NAME,
    description=DESCRIPTION,
    version="1.0.0",
    order=30,
    default_flags=ModuleFlag(
        enabled=True,
        stop_new_sales=False,
        terminate_services=False,
        maintenance_mode=False,
    ),
    icon="dns",
    tags=["dns", "proxy", "geo-unblock"],
    bot_keyboard=BotKeyboardConfig(
        text={"en": "🌐 SmartDNS", "fa": "🌐 SmartDNS"},
        description={
            "en": "Bypass geo-restrictions with Smart DNS proxy",
            "fa": "عبور از محدودیت‌های جغرافیایی با پروکسی DNS هوشمند",
        },
        row=1,
        column=0,
    ),
    admin_menu=AdminMenuConfig(
        label={"en": "SmartDNS Management", "fa": "مدیریت SmartDNS"},
        endpoint="/admin/smartdns",
        order=30,
    ),
    default_config={
        "max_profiles_per_user": 3,
        "dns_ttl_seconds": 300,
    },
)

__all__ = ["metadata"]