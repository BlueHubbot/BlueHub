"""
Game Server Services
======================
Business logic for game server lifecycle management:
- Provisioning (Docker container deployment)
- Power management (start/stop/restart)
- Backup/restore operations
- Player logging
- Console command execution via RCON
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit.logger import AuditLogger
from modules.game.models import GameServer, GameServerBackup, GameServerPlayerLog
from modules.game.schemas import (
    GameServerCreate,
    GameServerUpdate,
    GameBackupCreate,
    GameConsoleCommand,
    GameServerPowerAction,
)
from shared.models.enums import ServiceStatus
from shared.models.service import Service

logger = logging.getLogger("bluehub.modules.game.services")


# ------------------------------------------------------------------
# Custom exceptions
# ------------------------------------------------------------------

class GameServerError(Exception):
    """Base exception for game server errors."""


class GameServerNotFoundError(GameServerError):
    """Game server not found."""


class GameServerInvalidStateError(GameServerError):
    """Game server is in an invalid state for the requested operation."""


class GameServerDockerError(GameServerError):
    """Docker operation failed."""


class GameServerBackupError(GameServerError):
    """Backup or restore operation failed."""


class GameServerConsoleError(GameServerError):
    """Console command execution failed."""


# ------------------------------------------------------------------
# Docker image map per game type
# ------------------------------------------------------------------

GAME_DOCKER_IMAGES: dict[str, dict[str, Any]] = {
    "minecraft": {
        "image": "itzg/minecraft-server:latest",
        "internal_port": 25565,
        "protocol": "TCP",
        "env_defaults": {
            "EULA": "TRUE",
            "DIFFICULTY": "normal",
            "MODE": "survival",
            "ONLINE_MODE": "TRUE",
        },
    },
    "cs2": {
        "image": "cmaimone/cs2-server:latest",
        "internal_port": 27015,
        "protocol": "UDP",
        "env_defaults": {
            "GSLT": "",
            "SERVER_HOSTNAME": "BlueHub CS2 Server",
            "RCON_PASSWORD": "",
        },
    },
    "valheim": {
        "image": "lloesche/valheim-server:latest",
        "internal_port": 2456,
        "protocol": "UDP",
        "env_defaults": {
            "SERVER_NAME": "BlueHub Valheim",
            "SERVER_PASS": "",
            "WORLD_NAME": "BlueHubWorld",
        },
    },
    "voice": {
        "image": "ich777/teamspeak3-server:latest",
        "internal_port": 9987,
        "protocol": "UDP",
        "env_defaults": {
            "TS3_SERVER_LICENSE": "accept",
        },
    },
    "custom": {
        "image": "ubuntu:22.04",
        "internal_port": None,
        "protocol": "TCP",
        "env_defaults": {},
    },
}


# ------------------------------------------------------------------
# Main Service Class
# ------------------------------------------------------------------

class GameServerService:
    """
    Service layer for game server operations.
    Manages CRUD, Docker lifecycle, backups, and player logging.
    """

    def __init__(self, db: AsyncSession, audit: AuditLogger | None = None):
        self.db = db
        self.audit = audit or AuditLogger()

    # ──────────────────────────────────────────────
    # Helper: GameServer lookup
    # ──────────────────────────────────────────────

    async def _get_server(self, server_id: UUID) -> GameServer:
        """Fetch a GameServer by ID or raise."""
        result = await self.db.execute(
            select(GameServer).where(GameServer.id == server_id)
        )
        server = result.scalar_one_or_none()
        if not server:
            raise GameServerNotFoundError(f"Game server {server_id} not found")
        return server

    async def _get_server_by_service(self, service_id: UUID) -> GameServer:
        """Fetch a GameServer by service ID or raise."""
        result = await self.db.execute(
            select(GameServer).where(GameServer.service_id == service_id)
        )
        server = result.scalar_one_or_none()
        if not server:
            raise GameServerNotFoundError(
                f"Game server for service {service_id} not found"
            )
        return server

    # ──────────────────────────────────────────────
    # CRUD Operations
    # ──────────────────────────────────────────────

    async def create_server(
        self,
        data: GameServerCreate,
    ) -> GameServer:
        """Provision a new game server (create DB record + deploy Docker container)."""

        # Validate game type
        if data.game_type not in GAME_DOCKER_IMAGES:
            raise GameServerError(
                f"Unsupported game type: {data.game_type}. "
                f"Supported: {list(GAME_DOCKER_IMAGES.keys())}"
            )

        # Validate service exists
        result = await self.db.execute(
            select(Service).where(Service.id == data.service_id)
        )
        service = result.scalar_one_or_none()
        if not service:
            raise GameServerNotFoundError(
                f"Service {data.service_id} not found"
            )

        # Check for duplicate
        existing = await self.db.execute(
            select(GameServer).where(GameServer.service_id == data.service_id)
        )
        if existing.scalar_one_or_none():
            raise GameServerError(
                f"Game server already exists for service {data.service_id}"
            )

        docker_config = GAME_DOCKER_IMAGES[data.game_type]
        docker_image = docker_config["image"]
        internal_port = data.query_port or docker_config.get("internal_port")

        # Build env defaults
        env = dict(docker_config.get("env_defaults", {}))
        if data.extra_env:
            env.update(data.extra_env)

        # Build server_properties if not provided
        server_properties = data.server_properties or {}
        if data.game_type == "minecraft" and not server_properties:
            server_properties = {
                "max-players": str(data.max_players),
                "server-name": data.server_name,
                "motd": f"Welcome to {data.server_name} - BlueHub",
            }

        now = datetime.now(UTC)
        server = GameServer(
            id=uuid.uuid4(),
            service_id=data.service_id,
            game_type=data.game_type,
            game_version=data.game_version,
            server_name=data.server_name,
            status="provisioning",
            docker_image=docker_image,
            cpu_limit=data.cpu_limit,
            memory_limit_mb=data.memory_limit_mb,
            disk_limit_gb=data.disk_limit_gb,
            max_players=data.max_players,
            internal_port=internal_port,
            server_properties=server_properties or None,
            extra_env=env or None,
            notes=data.notes,
            created_at=now,
            updated_at=now,
        )

        self.db.add(server)
        await self.db.commit()
        await self.db.refresh(server)

        # Update service status to active
        await self.db.execute(
            update(Service)
            .where(Service.id == data.service_id)
            .values(
                status=ServiceStatus.ACTIVE,
                provisioned_at=now,
                service_metadata={
                    "game_server_id": str(server.id),
                    "game_type": data.game_type,
                    "server_name": data.server_name,
                },
            )
        )
        await self.db.commit()

        await self.audit.log(
            action="game_server.created",
            resource_type="game_server",
            resource_id=str(server.id),
            metadata={"game_type": data.game_type, "server_name": data.server_name},
        )

        logger.info(
            "Game server created: id=%s game=%s name=%s",
            server.id, data.game_type, data.server_name,
        )
        return server

    async def get_server(self, server_id: UUID) -> GameServer:
        """Get a game server by ID."""
        return await self._get_server(server_id)

    async def get_server_by_service(self, service_id: UUID) -> GameServer:
        """Get a game server by service ID."""
        return await self._get_server_by_service(service_id)

    async def list_servers(
        self,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,
        game_type: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[GameServer]:
        """List game servers with optional filters."""
        query = select(GameServer)

        if game_type:
            query = query.where(GameServer.game_type == game_type)
        if status:
            query = query.where(GameServer.status == status)

        # If scoped to a user, join through Service
        if user_id:
            query = query.join(Service, GameServer.service_id == Service.id).where(
                Service.user_id == user_id
            )
        if tenant_id:
            query = query.where(GameServer.service_id.in_(
                select(Service.id).where(Service.tenant_id == tenant_id)
            ))

        query = query.order_by(GameServer.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_server(
        self,
        server_id: UUID,
        data: GameServerUpdate,
    ) -> GameServer:
        """Update a game server's mutable fields."""
        server = await self._get_server(server_id)

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return server

        update_data["updated_at"] = datetime.now(UTC)

        await self.db.execute(
            update(GameServer)
            .where(GameServer.id == server_id)
            .values(**update_data)
        )
        await self.db.commit()
        await self.db.refresh(server)

        await self.audit.log(
            action="game_server.updated",
            resource_type="game_server",
            resource_id=str(server.id),
            metadata={"updated_fields": list(update_data.keys())},
        )

        return server

    async def delete_server(self, server_id: UUID) -> None:
        """Delete a game server record.

        Note: In production, this should also stop and remove the Docker container.
        """
        server = await self._get_server(server_id)

        # Stop the Docker container if running
        if server.docker_container_id and server.status in (
            "running", "starting",
        ):
            try:
                await self._docker_stop(server.docker_container_id)
            except GameServerDockerError:
                logger.warning(
                    "Failed to stop container %s for server %s",
                    server.docker_container_id, server_id,
                )

        # Update service status back to pending/cancelled
        await self.db.execute(
            update(Service)
            .where(Service.id == server.service_id)
            .values(status=ServiceStatus.CANCELLED)
        )

        # Delete game server (cascades to backups and player logs)
        await self.db.execute(
            delete(GameServer).where(GameServer.id == server_id)
        )
        await self.db.commit()

        await self.audit.log(
            action="game_server.deleted",
            resource_type="game_server",
            resource_id=str(server_id),
        )

    # ──────────────────────────────────────────────
    # Power Management (Docker passthrough)
    # ──────────────────────────────────────────────

    async def power_action(
        self,
        server_id: UUID,
        action: GameServerPowerAction,
    ) -> dict[str, Any]:
        """Execute a power action on a game server (start/stop/restart/kill)."""
        server = await self._get_server(server_id)

        valid_transitions = {
            "start": ("stopped", "error", "provisioning"),
            "stop": ("running", "starting"),
            "restart": ("running", "stopped", "error"),
            "kill": ("running", "starting", "stopping"),
        }

        allowed = valid_transitions.get(action.action, ())
        if server.status not in allowed:
            raise GameServerInvalidStateError(
                f"Cannot {action.action} server in status '{server.status}'. "
                f"Allowed statuses: {allowed}"
            )

        action_map = {
            "start": self._docker_start,
            "stop": self._docker_stop,
            "restart": self._docker_restart,
            "kill": self._docker_kill,
        }

        target_status = {
            "start": "running",
            "stop": "stopped",
            "restart": "running",
            "kill": "stopped",
        }

        now = datetime.now(UTC)

        try:
            func = action_map[action.action]

            # For start, we need to ensure the container exists first
            if action.action == "start" and not server.docker_container_id:
                # Attempt to create and start the container
                container_id = await self._docker_create(server)
                server.docker_container_id = container_id

            await func(server)

            new_status = target_status[action.action]

            update_values: dict[str, Any] = {
                "status": new_status,
                "updated_at": now,
            }
            if action.action == "start":
                update_values["last_started_at"] = now
            elif action.action in ("stop", "kill"):
                update_values["last_stopped_at"] = now
                update_values["uptime_seconds"] = 0

            await self.db.execute(
                update(GameServer)
                .where(GameServer.id == server_id)
                .values(**update_values)
            )
            await self.db.commit()
            await self.db.refresh(server)

        except GameServerDockerError as e:
            # Set server to error state
            await self.db.execute(
                update(GameServer)
                .where(GameServer.id == server_id)
                .values(status="error", error_message=str(e), updated_at=now)
            )
            await self.db.commit()
            raise

        await self.audit.log(
            action=f"game_server.{action.action}",
            resource_type="game_server",
            resource_id=str(server_id),
            metadata={"previous_status": server.status, "new_status": new_status},
        )

        return {
            "server_id": server_id,
            "action": action.action,
            "status": new_status,
            "message": f"Server {action.action} executed successfully",
        }

    # ──────────────────────────────────────────────
    # Docker Operations (placeholder implementations)
    # ──────────────────────────────────────────────

    async def _docker_create(self, server: GameServer) -> str:
        """Create a Docker container for the game server.

        In production, this uses the Docker SDK (docker-py) to create
        and start a container with the appropriate image, port mappings,
        resource limits, and environment variables.
        """
        container_id = f"game_{server.id.hex[:12]}"
        logger.info(
            "Docker create: container=%s image=%s game=%s",
            container_id, server.docker_image, server.game_type,
        )
        # Placeholder: In production, call docker SDK here
        return container_id

    async def _docker_start(self, server: GameServer) -> None:
        """Start the Docker container."""
        if not server.docker_container_id:
            raise GameServerDockerError("No Docker container associated with server")
        logger.info(
            "Docker start: container=%s", server.docker_container_id,
        )

    async def _docker_stop(self, container_id: str | GameServer) -> None:
        """Stop the Docker container."""
        cid = container_id if isinstance(container_id, str) else container_id.docker_container_id
        if not cid:
            raise GameServerDockerError("No Docker container to stop")
        logger.info("Docker stop: container=%s", cid)

    async def _docker_restart(self, server: GameServer) -> None:
        """Restart the Docker container."""
        if not server.docker_container_id:
            raise GameServerDockerError("No Docker container associated with server")
        logger.info(
            "Docker restart: container=%s", server.docker_container_id,
        )

    async def _docker_kill(self, server: GameServer) -> None:
        """Force-kill the Docker container."""
        if not server.docker_container_id:
            raise GameServerDockerError("No Docker container associated with server")
        logger.info(
            "Docker kill: container=%s", server.docker_container_id,
        )

    # ──────────────────────────────────────────────
    # Backup Operations
    # ──────────────────────────────────────────────

    async def create_backup(
        self,
        server_id: UUID,
        data: GameBackupCreate,
    ) -> GameServerBackup:
        """Create a manual backup of the game server's data directory."""
        server = await self._get_server(server_id)

        backup = GameServerBackup(
            id=uuid.uuid4(),
            server_id=server_id,
            backup_name=data.backup_name,
            status="pending",
            backup_type="manual",
            created_at=datetime.now(UTC),
        )
        self.db.add(backup)
        await self.db.commit()
        await self.db.refresh(backup)

        # In production, this would trigger an async task to tar/zip
        # the server's data volume and upload to S3/MinIO

        await self.audit.log(
            action="game_server.backup.created",
            resource_type="game_server_backup",
            resource_id=str(backup.id),
            metadata={"server_id": str(server_id), "backup_name": data.backup_name},
        )

        return backup

    async def list_backups(
        self,
        server_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[GameServerBackup]:
        """List backups for a game server."""
        server = await self._get_server(server_id)
        result = await self.db.execute(
            select(GameServerBackup)
            .where(GameServerBackup.server_id == server.id)
            .order_by(GameServerBackup.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def restore_backup(
        self,
        server_id: UUID,
        backup_id: UUID,
    ) -> dict[str, Any]:
        """Restore a game server from a backup."""
        server = await self._get_server(server_id)

        result = await self.db.execute(
            select(GameServerBackup).where(
                GameServerBackup.id == backup_id,
                GameServerBackup.server_id == server_id,
            )
        )
        backup = result.scalar_one_or_none()
        if not backup:
            raise GameServerBackupError(
                f"Backup {backup_id} not found for server {server_id}"
            )

        # Stop the server before restoring
        if server.status == "running":
            await self._docker_stop(server)

        # In production, this would extract the backup archive into
        # the server's data volume, then restart

        backup.status = "completed"
        backup.completed_at = datetime.now(UTC)
        await self.db.commit()

        await self.audit.log(
            action="game_server.restore",
            resource_type="game_server_backup",
            resource_id=str(backup_id),
            metadata={"server_id": str(server_id)},
        )

        return {
            "server_id": server_id,
            "backup_id": backup_id,
            "status": "restoring",
            "message": f"Restore from backup '{backup.backup_name}' initiated",
        }

    async def get_backup(self, backup_id: UUID) -> GameServerBackup:
        """Get a specific backup record."""
        result = await self.db.execute(
            select(GameServerBackup).where(GameServerBackup.id == backup_id)
        )
        backup = result.scalar_one_or_none()
        if not backup:
            raise GameServerBackupError(f"Backup {backup_id} not found")
        return backup

    async def delete_backup(self, backup_id: UUID) -> None:
        """Delete a backup record."""
        backup = await self.get_backup(backup_id)
        await self.db.execute(
            delete(GameServerBackup).where(GameServerBackup.id == backup_id)
        )
        await self.db.commit()

        await self.audit.log(
            action="game_server.backup.deleted",
            resource_type="game_server_backup",
            resource_id=str(backup_id),
        )

    # ──────────────────────────────────────────────
    # Console Commands
    # ──────────────────────────────────────────────

    async def execute_console(
        self,
        server_id: UUID,
        command: GameConsoleCommand,
    ) -> dict[str, Any]:
        """Send a console command to the game server via RCON or Docker exec."""
        server = await self._get_server(server_id)

        if server.status not in ("running", "starting"):
            raise GameServerInvalidStateError(
                f"Cannot execute command on server in status '{server.status}'. "
                "Server must be running."
            )

        # In production, this would use RCON (for Minecraft/CS2) or
        # `docker exec` to inject the command
        output = f"[simulated] Executed: {command.command}"

        logger.info(
            "Console command: server=%s command=%s", server_id, command.command,
        )

        return {
            "server_id": server_id,
            "command": command.command,
            "output": output,
            "success": True,
        }

    # ──────────────────────────────────────────────
    # Player Logging
    # ──────────────────────────────────────────────

    async def log_player_activity(
        self,
        server_id: UUID,
        player_name: str,
        player_uuid: str | None,
        action: str,
        ip_address: str | None = None,
        duration_seconds: int | None = None,
    ) -> GameServerPlayerLog:
        """Log a player connection event."""
        server = await self._get_server(server_id)

        log_entry = GameServerPlayerLog(
            id=uuid.uuid4(),
            server_id=server_id,
            player_name=player_name,
            player_uuid=player_uuid,
            action=action,
            ip_address=ip_address,
            duration_seconds=duration_seconds,
            created_at=datetime.now(UTC),
        )
        self.db.add(log_entry)

        # Update player count stats
        if action == "join":
            await self.db.execute(
                update(GameServer)
                .where(GameServer.id == server_id)
                .values(
                    player_count=GameServer.player_count + 1,
                    total_connections=GameServer.total_connections + 1,
                    updated_at=datetime.now(UTC),
                )
            )
        elif action == "leave":
            await self.db.execute(
                update(GameServer)
                .where(GameServer.id == server_id)
                .values(
                    player_count=GameServer.player_count - 1,
                    updated_at=datetime.now(UTC),
                )
            )

        await self.db.commit()
        return log_entry

    async def list_player_logs(
        self,
        server_id: UUID,
        player_name: str | None = None,
        action: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[GameServerPlayerLog]:
        """List player activity logs for a server."""
        server = await self._get_server(server_id)

        query = select(GameServerPlayerLog).where(
            GameServerPlayerLog.server_id == server.id
        )
        if player_name:
            query = query.where(GameServerPlayerLog.player_name == player_name)
        if action:
            query = query.where(GameServerPlayerLog.action == action)

        query = query.order_by(GameServerPlayerLog.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ──────────────────────────────────────────────
    # Status & Stats
    # ──────────────────────────────────────────────

    async def get_server_status(self, server_id: UUID) -> dict[str, Any]:
        """Get detailed status of a game server (including live stats)."""
        server = await self._get_server(server_id)

        return {
            "server_id": server.id,
            "status": server.status,
            "player_count": server.player_count,
            "max_players": server.max_players,
            "uptime_seconds": server.uptime_seconds,
            "total_connections": server.total_connections,
            "cpu_limit": server.cpu_limit,
            "memory_limit_mb": server.memory_limit_mb,
            "disk_limit_gb": server.disk_limit_gb,
            "docker_container_id": server.docker_container_id,
            "docker_image": server.docker_image,
            "host_port": server.host_port,
            "ip_address": server.ip_address,
            "last_started_at": server.last_started_at,
            "last_stopped_at": server.last_stopped_at,
            "last_backup_at": server.last_backup_at,
            "auto_backup_enabled": server.auto_backup_enabled,
            "error_message": server.error_message,
        }


__all__ = [
    "GameServerService",
    "GameServerError",
    "GameServerNotFoundError",
    "GameServerInvalidStateError",
    "GameServerDockerError",
    "GameServerBackupError",
    "GameServerConsoleError",
]