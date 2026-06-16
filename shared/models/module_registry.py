"""
BlueHub Module Registry Model
===============================
SQLAlchemy ORM model for module registration, versioning, and feature flags.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import CoreBase, TimestampMixin, UUIDMixin


class ModuleRegistry(UUIDMixin, TimestampMixin, CoreBase):
    """
    Module registry for plug-and-play feature modules.
    Controls which modules are enabled and their configuration.
    """

    __tablename__ = "module_registry"

    module_name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique module identifier (vpn, vps, smartdns, streaming, game)",
    )
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Human-readable module display name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Module description for admin UI",
    )
    version: Mapped[str] = mapped_column(
        String(20),
        default="1.0.0",
        nullable=False,
        doc="Module version (semver)",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the module is enabled system-wide",
    )
    order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Display/processing order priority",
    )
    config_schema: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        doc="JSON Schema for module configuration validation",
    )
    flags: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        doc="Feature flags: stop_new_sales, terminate_services, maintenance_mode",
    )

    def __repr__(self) -> str:
        return (
            f"<ModuleRegistry(name={self.module_name!r}, "
            f"enabled={self.enabled}, version={self.version!r})>"
        )


__all__ = ["ModuleRegistry"]
