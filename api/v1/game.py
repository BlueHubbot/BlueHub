"""
BlueHub Game Server API Endpoints
===================================
FastAPI router for Game Server hosting management: provisioning,
power management, backups, console commands, and player logging.

Covers both admin and client-facing endpoints for the Game module.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.auth import get_current_user
from dependencies.db import get_async_session
from modules.game.schemas import (
    GameBackupCreate,
    GameBackupResponse,
    GameConsoleCommand,
    GameConsoleResponse,
    GamePlayerLogResponse,
    GameRestoreRequest,
    GameRestoreResponse,
    GameServerCreate,
    GameServerPowerAction,
    GameServerPowerResponse,
    GameServerResponse,
    GameServerStatusResponse,
    GameServerSummary,
    GameServerUpdate,
)
from modules.game.services import (
    GameServerBackupError,
    GameServerError,
    GameServerInvalidStateError,
    GameServerNotFoundError,
    GameServerService,
)
from shared.models.product import Product
from shared.models.service import Service, ServiceStatus
from shared.models.user import User

router = APIRouter(prefix="/game", tags=["Game"])


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────


def _require_admin(current_user: User) -> None:
    """Check if the authenticated user has admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )


def _build_game_response(server: Any) -> GameServerResponse:
    """Build a GameServerResponse from a GameServer model instance."""
    import datetime
    return GameServerResponse(
        id=server.id,
        service_id=server.service_id,
        game_type=server.game_type,
        game_version=server.game_version,
        server_name=server.server_name,
        status=server.status,
        docker_container_id=server.docker_container_id,
        docker_image=server.docker_image,
        host_port=server.host_port,
        internal_port=server.internal_port,
        cpu_limit=server.cpu_limit,
        memory_limit_mb=server.memory_limit_mb,
        disk_limit_gb=server.disk_limit_gb,
        ip_address=server.ip_address,
        query_port=server.query_port,
        rcon_port=server.rcon_port,
        rcon_password=server.rcon_password,
        ftp_port=server.ftp_port,
        ftp_username=server.ftp_username,
        ftp_password=server.ftp_password,
        server_properties=server.server_properties,
        extra_env=server.extra_env,
        plugins=server.plugins,
        whitelist=server.whitelist,
        ops_list=server.ops_list,
        banned_players=server.banned_players,
        auto_backup_enabled=server.auto_backup_enabled,
        backup_interval_hours=server.backup_interval_hours,
        max_backups=server.max_backups,
        uptime_seconds=server.uptime_seconds,
        player_count=server.player_count,
        max_players=server.max_players,
        total_connections=server.total_connections,
        last_started_at=server.last_started_at,
        last_stopped_at=server.last_stopped_at,
        last_backup_at=server.last_backup_at,
        error_message=server.error_message,
        extra_config=server.extra_config,
        notes=server.notes,
        created_at=server.created_at,
        updated_at=server.updated_at,
    )


def _build_summary_response(server: Any) -> GameServerSummary:
    """Build a lightweight GameServerSummary from a GameServer."""
    return GameServerSummary(
        id=server.id,
        service_id=server.service_id,
        game_type=server.game_type,
        game_version=server.game_version,
        server_name=server.server_name,
        status=server.status,
        host_port=server.host_port,
        cpu_limit=server.cpu_limit,
        memory_limit_mb=server.memory_limit_mb,
        disk_limit_gb=server.disk_limit_gb,
        player_count=server.player_count,
        max_players=server.max_players,
        uptime_seconds=server.uptime_seconds,
        created_at=server.created_at,
    )


async def _check_server_ownership(
    server: Any,
    session: AsyncSession,
    current_user: User,
) -> None:
    """Raise 403 if the current user does not own the service tied to this server."""
    if current_user.is_admin:
        return
    service = await session.get(Service, server.service_id)
    if service is None or str(service.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not own this game server",
        )


# ──────────────────────────────────────────────
# Game Server CRUD
# ──────────────────────────────────────────────


@router.post(
    "/servers",
    response_model=GameServerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_game_server(
    body: GameServerCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> GameServerResponse:
    """
    Provision a new game server.

    Creates the Docker container and returns the server record.
    Requires admin privileges.
    """
    _require_admin(current_user)

    game_service = GameServerService(session)
    try:
        server = await game_service.create_server(body)
    except GameServerError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return _build_game_response(server)


@router.get("/servers", response_model=list[GameServerSummary])
async def list_game_servers(
    game_type: str | None = Query(None, description="Filter by game type"),
    status_filter: str | None = Query(None, alias="status", description="Filter by server status"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[GameServerSummary]:
    """
    List game servers with optional filters.

    Admin: sees all servers. Client: sees only their own services' servers.
    """
    game_service = GameServerService(session)

    servers = await game_service.list_servers(
        game_type=game_type,
        status=status_filter,
        skip=offset,
        limit=limit,
    )

    # Non-admins can only see servers tied to their own services
    if not current_user.is_admin:
        user_services_stmt = select(Service.id).where(
            Service.user_id == str(current_user.id)
        )
        result = await session.execute(user_services_stmt)
        user_service_ids = {str(row[0]) for row in result.all()}
        servers = [
            s for s in servers if str(s.service_id) in user_service_ids
        ]

    return [_build_summary_response(s) for s in servers]


@router.get("/servers/{server_id}", response_model=GameServerResponse)
async def get_game_server(
    server_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> GameServerResponse:
    """
    Get a single game server by ID with full details.
    """
    game_service = GameServerService(session)
    try:
        server = await game_service.get_server(server_id)
    except GameServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    await _check_server_ownership(server, session, current_user)
    return _build_game_response(server)


@router.patch("/servers/{server_id}", response_model=GameServerResponse)
async def update_game_server(
    server_id: UUID,
    body: GameServerUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> GameServerResponse:
    """
    Update a game server's mutable fields (name, resources, config).

    Does NOT affect the running Docker container.
    Requires admin privileges.
    """
    _require_admin(current_user)

    game_service = GameServerService(session)
    try:
        server = await game_service.update_server(server_id, body)
    except GameServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _build_game_response(server)


@router.delete("/servers/{server_id}")
async def delete_game_server(
    server_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """
    Decommission a game server.

    Destroys the Docker container and removes the database record.
    Requires admin privileges.
    """
    _require_admin(current_user)

    game_service = GameServerService(session)
    try:
        await game_service.delete_server(server_id)
    except GameServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return {"detail": "Game server deleted successfully"}


# ──────────────────────────────────────────────
# Power Actions
# ──────────────────────────────────────────────


@router.post(
    "/servers/{server_id}/power",
    response_model=GameServerPowerResponse,
)
async def power_action_server(
    server_id: UUID,
    body: GameServerPowerAction,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> GameServerPowerResponse:
    """
    Execute a power action on a game server.

    Supported actions: start, stop, restart, kill.
    Requires admin privileges.
    """
    _require_admin(current_user)

    game_service = GameServerService(session)
    try:
        result = await game_service.power_action(server_id, body)
    except GameServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except GameServerInvalidStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except GameServerError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return GameServerPowerResponse(
        server_id=result["server_id"],
        action=result["action"],
        status=result["status"],
        message=result["message"],
    )


# ──────────────────────────────────────────────
# Status
# ──────────────────────────────────────────────


@router.get(
    "/servers/{server_id}/status",
    response_model=GameServerStatusResponse,
)
async def get_server_status(
    server_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> GameServerStatusResponse:
    """
    Get detailed status of a game server.

    Returns live stats including player count, uptime, and Docker info.
    """
    game_service = GameServerService(session)
    try:
        server = await game_service.get_server(server_id)
    except GameServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    await _check_server_ownership(server, session, current_user)
    status_data = await game_service.get_server_status(server_id)
    return GameServerStatusResponse(**status_data)


# ──────────────────────────────────────────────
# Console Commands
# ──────────────────────────────────────────────


@router.post(
    "/servers/{server_id}/console",
    response_model=GameConsoleResponse,
)
async def execute_console_command(
    server_id: UUID,
    body: GameConsoleCommand,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> GameConsoleResponse:
    """
    Send a console command to a running game server.

    Uses RCON (for Minecraft/CS2) or Docker exec to inject commands.
    Server must be running.
    """
    game_service = GameServerService(session)
    try:
        result = await game_service.execute_console(server_id, body)
    except GameServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except GameServerInvalidStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    await _check_server_ownership(
        (await game_service.get_server(server_id)), session, current_user
    )

    return GameConsoleResponse(
        server_id=result["server_id"],
        command=result["command"],
        output=result["output"],
        success=result["success"],
    )


# ──────────────────────────────────────────────
# Backups
# ──────────────────────────────────────────────


@router.post(
    "/servers/{server_id}/backups",
    response_model=GameBackupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_game_backup(
    server_id: UUID,
    body: GameBackupCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> GameBackupResponse:
    """
    Create a manual backup of a game server's data directory.
    """
    game_service = GameServerService(session)
    try:
        backup = await game_service.create_backup(server_id, body)
    except GameServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except GameServerError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return GameBackupResponse(
        id=backup.id,
        server_id=backup.server_id,
        backup_name=backup.backup_name,
        file_path=backup.file_path,
        file_size_bytes=backup.file_size_bytes,
        status=backup.status,
        backup_type=backup.backup_type,
        error_message=backup.error_message,
        created_at=backup.created_at,
        completed_at=backup.completed_at,
    )


@router.get(
    "/servers/{server_id}/backups",
    response_model=list[GameBackupResponse],
)
async def list_game_backups(
    server_id: UUID,
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[GameBackupResponse]:
    """
    List backups for a game server.
    """
    game_service = GameServerService(session)

    # Verify ownership
    try:
        server = await game_service.get_server(server_id)
    except GameServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    await _check_server_ownership(server, session, current_user)

    backups = await game_service.list_backups(
        server_id, skip=offset, limit=limit
    )
    return [
        GameBackupResponse(
            id=b.id,
            server_id=b.server_id,
            backup_name=b.backup_name,
            file_path=b.file_path,
            file_size_bytes=b.file_size_bytes,
            status=b.status,
            backup_type=b.backup_type,
            error_message=b.error_message,
            created_at=b.created_at,
            completed_at=b.completed_at,
        )
        for b in backups
    ]


@router.post(
    "/servers/{server_id}/restore",
    response_model=GameRestoreResponse,
)
async def restore_game_backup(
    server_id: UUID,
    body: GameRestoreRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> GameRestoreResponse:
    """
    Restore a game server from a backup.

    Stops the server, restores files, and optionally restarts.
    """
    _require_admin(current_user)

    game_service = GameServerService(session)
    try:
        result = await game_service.restore_backup(
            server_id, body.backup_id
        )
    except (GameServerNotFoundError, GameServerBackupError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except GameServerError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return GameRestoreResponse(
        server_id=result["server_id"],
        backup_id=result["backup_id"],
        status=result["status"],
        message=result["message"],
    )


# ──────────────────────────────────────────────
# Player Logs
# ──────────────────────────────────────────────


@router.get(
    "/servers/{server_id}/players",
    response_model=list[GamePlayerLogResponse],
)
async def list_game_player_logs(
    server_id: UUID,
    player_name: str | None = Query(None, description="Filter by player name"),
    action: str | None = Query(None, description="Filter by action (join/leave)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[GamePlayerLogResponse]:
    """
    List player activity logs for a game server.
    """
    game_service = GameServerService(session)

    # Verify ownership
    try:
        server = await game_service.get_server(server_id)
    except GameServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    await _check_server_ownership(server, session, current_user)

    logs = await game_service.list_player_logs(
        server_id,
        player_name=player_name,
        action=action,
        skip=offset,
        limit=limit,
    )
    return [
        GamePlayerLogResponse(
            id=log.id,
            server_id=log.server_id,
            player_name=log.player_name,
            player_uuid=log.player_uuid,
            action=log.action,
            ip_address=log.ip_address,
            duration_seconds=log.duration_seconds,
            created_at=log.created_at,
        )
        for log in logs
    ]


# ──────────────────────────────────────────────
# Game Products (Client-facing)
# ──────────────────────────────────────────────


@router.get("/products")
async def list_game_products(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    List available game server products for purchase.

    Returns public product details including game type and pricing.
    """
    stmt = select(Product).where(
        Product.module == "game",
        Product.is_active.is_(True),
    )
    result = await session.execute(stmt)
    products = result.scalars().all()

    return [
        {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "game_type": p.features.get("game_type", "minecraft") if p.features else "minecraft",
            "cpu_limit": p.features.get("cpu_limit", 1.0) if p.features else 1.0,
            "memory_limit_mb": p.features.get("memory_limit_mb", 1024) if p.features else 1024,
            "disk_limit_gb": p.features.get("disk_limit_gb", 10) if p.features else 10,
            "max_players": p.features.get("max_players", 20) if p.features else 20,
            "backup_included": p.features.get("backup_included", True) if p.features else True,
            "price_monthly": float(p.price_monthly) if p.price_monthly else None,
            "price_quarterly": float(p.price_quarterly) if p.price_quarterly else None,
            "price_semi_annually": float(p.price_semi_annually) if p.price_semi_annually else None,
            "price_annually": float(p.price_annually) if p.price_annually else None,
            "is_active": p.is_active,
        }
        for p in products
    ]


# ──────────────────────────────────────────────
# Game Services (User-facing list)
# ──────────────────────────────────────────────


@router.get("/services")
async def list_my_game_services(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    List the current user's game server services with associated servers and status.

    Returns active and suspended game services owned by the authenticated user.
    """
    from sqlalchemy.orm import selectinload

    stmt = (
        select(Service)
        .options(selectinload(Service.game_servers))
        .where(
            Service.user_id == str(current_user.id),
            Service.status.in_([ServiceStatus.ACTIVE, ServiceStatus.SUSPENDED]),
        )
        .order_by(Service.created_at.desc())
    )
    result = await session.execute(stmt)
    services = result.scalars().all()

    items: list[dict[str, Any]] = []
    for svc in services:
        for gs in svc.game_servers or []:
            items.append({
                "service_id": str(svc.id),
                "server_id": str(gs.id),
                "game_type": gs.game_type,
                "game_version": gs.game_version,
                "server_name": gs.server_name,
                "status": gs.status,
                "host_port": gs.host_port,
                "ip_address": gs.ip_address,
                "player_count": gs.player_count,
                "max_players": gs.max_players,
                "cpu_limit": gs.cpu_limit,
                "memory_limit_mb": gs.memory_limit_mb,
                "disk_limit_gb": gs.disk_limit_gb,
                "service_status": svc.status.value if hasattr(svc.status, "value") else str(svc.status),
                "expires_at": svc.expires_at,
                "created_at": gs.created_at,
            })
        # If service has no game servers yet, still show the service
        if not svc.game_servers:
            items.append({
                "service_id": str(svc.id),
                "server_id": None,
                "game_type": None,
                "game_version": None,
                "server_name": None,
                "status": "pending",
                "host_port": None,
                "ip_address": None,
                "player_count": None,
                "max_players": None,
                "cpu_limit": None,
                "memory_limit_mb": None,
                "disk_limit_gb": None,
                "service_status": svc.status.value if hasattr(svc.status, "value") else str(svc.status),
                "expires_at": svc.expires_at,
                "created_at": svc.created_at,
            })

    return {"services": items, "total": len(items)}


__all__ = ["router"]