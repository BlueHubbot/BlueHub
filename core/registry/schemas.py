"""
BlueHub Module Registry Schemas
================================
Pydantic models for module metadata, feature flags, and configuration.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ModuleStatus(str, Enum):
    """Operational status of a module."""

    ACTIVE = "active"
    STOP_NEW_SALES = "stop_new_sales"
    TERMINATE_SERVICES = "terminate_services"
    DISABLED = "disabled"


class ModuleFlag(BaseModel):
    """Feature flag configuration for a module."""

    enabled: bool = Field(default=True, description="Whether module is enabled")
    stop_new_sales: bool = Field(
        default=False,
        description="Stop new sales for this module",
    )
    terminate_services: bool = Field(
        default=False,
        description="Terminate all services for this module",
    )
    maintenance_mode: bool = Field(
        default=False,
        description="Put module into maintenance mode",
    )


class BotKeyboardConfig(BaseModel):
    """Telegram bot keyboard configuration for a module."""

    text: str | dict[str, str] = Field(..., description="Button label (string or i18n dict)")
    description: str | dict[str, str] = Field(default="", description="Button description (string or i18n dict)")
    row: int = Field(default=0, description="Keyboard row position")
    column: int = Field(default=0, description="Keyboard column position")


class AdminMenuConfig(BaseModel):
    """Admin panel menu configuration for a module."""

    label: str | dict[str, str] = Field(..., description="Menu label (string or i18n dict)")
    endpoint: str = Field(default="", description="Admin panel route endpoint")
    icon: str | None = Field(default=None, description="Menu icon identifier")
    order: int = Field(default=10, description="Menu display order")


class ModuleMetadata(BaseModel):
    """
    Metadata defining a pluggable service module.
    Scanned from modules/<name>/metadata.py on startup.
    """

    name: str = Field(..., description="Unique module identifier")
    display_name: str | dict[str, str] = Field(..., description="Human-readable module name (string or i18n dict)")
    description: str | dict[str, str] = Field(default="", description="Module description (string or i18n dict)")
    version: str = Field(default="1.0.0", description="Module version (semver)")
    order: int = Field(default=0, description="Display/processing order")
    config_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema for module configuration",
    )
    default_flags: ModuleFlag = Field(
        default_factory=ModuleFlag,
        description="Default feature flag values",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of module names this module depends on",
    )
    icon: str | None = Field(
        default=None,
        description="Icon identifier for admin UI",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorisation",
    )
    bot_keyboard: BotKeyboardConfig | None = Field(
        default=None,
        description="Telegram bot keyboard configuration",
    )
    admin_menu: AdminMenuConfig | None = Field(
        default=None,
        description="Admin panel menu configuration",
    )
    default_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Default module configuration values",
    )


class ModuleRegistryResponse(BaseModel):
    """Response schema for module registry API."""

    id: str | None = Field(default=None, description="Database ID")
    module_name: str = Field(..., description="Unique module identifier")
    display_name: str = Field(..., description="Module display name")
    description: str | None = Field(default=None, description="Module description")
    version: str = Field(..., description="Module version")
    enabled: bool = Field(..., description="Whether module is enabled")
    order: int = Field(default=0, description="Display order")
    flags: ModuleFlag = Field(
        default_factory=ModuleFlag,
        description="Feature flags",
    )


class ModuleToggleRequest(BaseModel):
    """Request schema for toggling module state."""

    enabled: bool | None = Field(default=None, description="Enable/disable module")
    stop_new_sales: bool | None = Field(
        default=None,
        description="Stop new sales flag",
    )
    terminate_services: bool | None = Field(
        default=None,
        description="Terminate services flag",
    )
    maintenance_mode: bool | None = Field(
        default=None,
        description="Maintenance mode flag",
    )


__all__ = [
    "AdminMenuConfig",
    "BotKeyboardConfig",
    "ModuleFlag",
    "ModuleMetadata",
    "ModuleRegistryResponse",
    "ModuleStatus",
    "ModuleToggleRequest",
]
