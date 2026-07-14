"""
Game Server Module Database Models
====================================
SQLAlchemy ORM models for game server hosting:
- GameServer: tracks game server instances (Minecraft, CS2, Valheim, etc.)
- GameServerBackup: stores backup metadata for server restores
- GameServerPlayerLog: tracks player connections for monitoring
"""

from __future__ import annotations

import uuid as _uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import CoreBase

if TYPE_CHECKING:
    from shared.models.service import Service


class GameServer(CoreBase):
    """Game server instance linked to a billing service (one-to-one)."""

    __tablename__ = "game_servers"

    id: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4
    )
    service_id: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    game_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        doc="Game type: minecraft, cs2, valheim, voice, custom"
    )
    game_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True, doc="Game version (e.g., 1.20.4)"
    )
    server_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="provisioning", index=True
    )
    docker_container_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    docker_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    host_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    internal_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_limit: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=1024)
    disk_limit_gb: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    query_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rcon_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rcon_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ftp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ftp_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ftp_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    server_properties: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    extra_env: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    plugins: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    whitelist: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    ops_list: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    banned_players: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    auto_backup_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    backup_interval_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    max_backups: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    uptime_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    player_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_players: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    total_connections: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_backup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Relationships
    service: Mapped["Service"] = relationship(
        "Service", back_populates="game_servers", lazy="selectin", uselist=False
    )
    backups: Mapped[list["GameServerBackup"]] = relationship(
        "GameServerBackup", back_populates="server", lazy="selectin",
        cascade="all, delete-orphan"
    )
    player_logs: Mapped[list["GameServerPlayerLog"]] = relationship(
        "GameServerPlayerLog", back_populates="server", lazy="selectin",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<GameServer(id={self.id}, game={self.game_type!r}, "
            f"name={self.server_name!r}, status={self.status!r})>"
        )


class GameServerBackup(CoreBase):
    """Backup record for a game server."""

    __tablename__ = "game_server_backups"

    id: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4
    )
    server_id: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_servers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    backup_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    backup_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="auto"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    server: Mapped["GameServer"] = relationship("GameServer", back_populates="backups")


class GameServerPlayerLog(CoreBase):
    """Player connection log for a game server."""

    __tablename__ = "game_server_player_logs"

    id: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4
    )
    server_id: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_servers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    player_name: Mapped[str] = mapped_column(String(100), nullable=False)
    player_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    # Relationships
    server: Mapped["GameServer"] = relationship("GameServer", back_populates="player_logs")


__all__ = ["GameServer", "GameServerBackup", "GameServerPlayerLog"]