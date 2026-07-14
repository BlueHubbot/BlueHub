"""
Game Server Module Schemas
============================
Pydantic request/response schemas for game server hosting:
- GameServer CRUD and lifecycle management
- Backup management
- Player log queries
- Power actions (start/stop/restart)
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------
# Game Server base schemas
# ------------------------------------------------------------------

class GameServerCreate(BaseModel):
    """Schema for provisioning a new game server."""

    service_id: UUID = Field(..., description="Associated billing service ID")
    game_type: str = Field(
        ...,
        pattern=r"^(minecraft|cs2|valheim|voice|custom)$",
        description="Game type identifier",
    )
    game_version: str | None = Field(
        default=None, max_length=50,
        description="Game version (e.g., 1.20.4 for Minecraft)",
    )
    server_name: str = Field(
        ..., min_length=1, max_length=100,
        description="Human-readable server name",
    )
    cpu_limit: float = Field(
        default=1.0, ge=0.1, le=32.0,
        description="CPU cores limit",
    )
    memory_limit_mb: int = Field(
        default=1024, ge=256, le=65536,
        description="Memory limit in MB",
    )
    disk_limit_gb: int = Field(
        default=10, ge=1, le=1000,
        description="Disk limit in GB",
    )
    max_players: int = Field(
        default=20, ge=1, le=500,
        description="Maximum concurrent players",
    )
    query_port: int | None = Field(
        default=None, ge=1024, le=65535,
        description="Game query port",
    )
    server_properties: dict | None = Field(
        default=None,
        description="Game-specific server properties (e.g., server.properties for MC)",
    )
    extra_env: dict | None = Field(
        default=None,
        description="Extra environment variables for Docker container",
    )
    notes: str | None = Field(default=None, max_length=2000)


class GameServerUpdate(BaseModel):
    """Schema for updating an existing game server."""

    server_name: str | None = Field(default=None, max_length=100)
    cpu_limit: float | None = Field(default=None, ge=0.1, le=32.0)
    memory_limit_mb: int | None = Field(default=None, ge=256, le=65536)
    disk_limit_gb: int | None = Field(default=None, ge=1, le=1000)
    max_players: int | None = Field(default=None, ge=1, le=500)
    server_properties: dict | None = None
    extra_env: dict | None = None
    plugins: dict | None = None
    whitelist: list[str] | None = None
    ops_list: list[str] | None = None
    banned_players: list[str] | None = None
    auto_backup_enabled: bool | None = None
    backup_interval_hours: int | None = Field(default=None, ge=1, le=168)
    max_backups: int | None = Field(default=None, ge=1, le=30)
    notes: str | None = Field(default=None, max_length=2000)


class GameServerResponse(BaseModel):
    """Full game server response returned to API consumers."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_id: UUID
    game_type: str
    game_version: str | None
    server_name: str
    status: str
    docker_container_id: str | None
    docker_image: str | None
    host_port: int | None
    internal_port: int | None
    cpu_limit: float
    memory_limit_mb: int
    disk_limit_gb: int
    ip_address: str | None
    query_port: int | None
    rcon_port: int | None
    rcon_password: str | None
    ftp_port: int | None
    ftp_username: str | None
    ftp_password: str | None
    server_properties: dict | None
    extra_env: dict | None
    plugins: dict | None
    whitelist: list[str] | None
    ops_list: list[str] | None
    banned_players: list[str] | None
    auto_backup_enabled: bool
    backup_interval_hours: int
    max_backups: int
    uptime_seconds: int
    player_count: int
    max_players: int
    total_connections: int
    last_started_at: datetime | None
    last_stopped_at: datetime | None
    last_backup_at: datetime | None
    error_message: str | None
    extra_config: dict | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class GameServerSummary(BaseModel):
    """Lightweight game server representation for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_id: UUID
    game_type: str
    game_version: str | None
    server_name: str
    status: str
    host_port: int | None
    cpu_limit: float
    memory_limit_mb: int
    disk_limit_gb: int
    player_count: int
    max_players: int
    uptime_seconds: int
    created_at: datetime


# ------------------------------------------------------------------
# Power action schemas
# ------------------------------------------------------------------

class GameServerPowerAction(BaseModel):
    """Schema for power actions on a game server."""

    action: str = Field(
        ...,
        pattern=r"^(start|stop|restart|kill)$",
        description="Power action to execute",
    )


class GameServerPowerResponse(BaseModel):
    """Response after executing a power action."""

    server_id: UUID
    action: str
    status: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now())


# ------------------------------------------------------------------
# Backup schemas
# ------------------------------------------------------------------

class GameBackupCreate(BaseModel):
    """Schema for creating a manual backup."""

    backup_name: str = Field(..., min_length=1, max_length=255)


class GameBackupResponse(BaseModel):
    """Backup record response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    server_id: UUID
    backup_name: str
    file_path: str | None
    file_size_bytes: int | None
    status: str
    backup_type: str
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class GameRestoreRequest(BaseModel):
    """Schema for restoring a server from backup."""

    backup_id: UUID = Field(..., description="Backup ID to restore from")


class GameRestoreResponse(BaseModel):
    """Response after initiating a restore operation."""

    server_id: UUID
    backup_id: UUID
    status: str = "restoring"
    message: str


# ------------------------------------------------------------------
# Player log schemas
# ------------------------------------------------------------------

class GamePlayerLogResponse(BaseModel):
    """Player connection log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    server_id: UUID
    player_name: str
    player_uuid: str | None
    action: str
    ip_address: str | None
    duration_seconds: int | None
    created_at: datetime


# ------------------------------------------------------------------
# Status and console schemas
# ------------------------------------------------------------------

class GameServerStatusResponse(BaseModel):
    """Detailed status information for a game server."""

    server_id: UUID
    status: str
    player_count: int
    max_players: int
    uptime_seconds: int
    total_connections: int
    cpu_limit: float
    memory_limit_mb: int
    disk_limit_gb: int
    docker_container_id: str | None
    docker_image: str | None
    host_port: int | None
    ip_address: str | None
    last_started_at: datetime | None
    last_stopped_at: datetime | None
    last_backup_at: datetime | None
    auto_backup_enabled: bool
    error_message: str | None


class GameConsoleCommand(BaseModel):
    """Schema for sending a console command to a game server."""

    command: str = Field(
        ..., min_length=1, max_length=1000,
        description="Console command to execute",
    )


class GameConsoleResponse(BaseModel):
    """Response from a console command execution."""

    server_id: UUID
    command: str
    output: str = ""
    success: bool = True
    error: str | None = None


__all__ = [
    "GameServerCreate",
    "GameServerUpdate",
    "GameServerResponse",
    "GameServerSummary",
    "GameServerPowerAction",
    "GameServerPowerResponse",
    "GameBackupCreate",
    "GameBackupResponse",
    "GameRestoreRequest",
    "GameRestoreResponse",
    "GamePlayerLogResponse",
    "GameServerStatusResponse",
    "GameConsoleCommand",
    "GameConsoleResponse",
]