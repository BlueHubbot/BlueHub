"""
VPS Module Metadata
===================
Module definition for VPS services (virtual private servers).
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
    "en": "VPS Service",
    "fa": "سرویس VPS",
}

DESCRIPTION: dict[str, str] = {
    "en": "Virtual Private Server services with KVM-based virtualization and SSD storage",
    "fa": "سرویس‌های سرور مجازی با مجازی‌سازی KVM و ذخیره‌سازی SSD",
}

# ------------------------------------------------------------------
# Metadata
# ------------------------------------------------------------------

metadata = ModuleMetadata(
    name="vps",
    display_name=DISPLAY_NAME,
    description=DESCRIPTION,
    version="1.0.0",
    order=20,
    default_flags=ModuleFlag(
        enabled=True,
        stop_new_sales=False,
        terminate_services=False,
        maintenance_mode=False,
    ),
    icon="cloud",
    tags=["compute", "virtualization", "cloud"],
    bot_keyboard=BotKeyboardConfig(
        text={"en": "🖥 VPS", "fa": "🖥 وی‌پی‌اس"},
        description={
            "en": "Virtual private servers, snapshots, and management",
            "fa": "سرورهای مجازی، اسنپ‌شات و مدیریت",
        },
        row=2,
        column=1,
    ),
    admin_menu=AdminMenuConfig(
        label={"en": "VPS Management", "fa": "مدیریت VPS"},
        endpoint="/admin/vps",
        order=20,
    ),
    default_config={
        "max_instances_per_user": 5,
        "snapshot_limit_per_instance": 3,
        "auto_backup_enabled": True,
    },
)

__all__ = ["metadata"]
