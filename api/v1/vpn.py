"""
BlueHub VPN API Endpoints
===========================
FastAPI router for VPN account management: provisioning, server management,
traffic monitoring, configuration downloads, and session tracking.

Covers both admin and client-facing endpoints for the VPN module.
"""

from __future__ import annotations

import base64
import io
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import qrcode  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    qrcode = None

from dependencies.auth import get_current_user
from dependencies.db import get_async_session
from modules.vpn.models import VpnAccount, VpnServer
from modules.vpn.schemas import (
    VpnAccountCreate,
    VpnAccountResponse,
    VpnAccountUpdate,
    VpnConfigResponse,
    VpnProductResponse,
    VpnPurchaseRequest,
    VpnPurchaseResponse,
    VpnServerCreate,
    VpnServerResponse,
    VpnServerUpdate,
    VpnServiceListItem,
    VpnServiceListResponse,
    VpnTrafficResponse,
)
from modules.vpn.services import (
    AccountTrafficSummary,
    VpnAccountService,
    VpnConfigGenerationError,
    VpnProvisioningError,
    VpnServiceError,
)
from modules.vpn.vpn_servers import VpnServerService
from shared.models.enums import VpnAccountStatus, VpnProtocol
from shared.models.service import Service, ServiceStatus
from shared.models.user import User

router = APIRouter(prefix="/vpn", tags=["VPN"])


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────


def _build_account_response(account: VpnAccount) -> VpnAccountResponse:
    """Build a VpnAccountResponse from a VpnAccount model instance."""
    from modules.vpn.schemas import VpnProtocolConfigSchema, VpnSessionSchema

    return VpnAccountResponse(
        id=str(account.id),
        service_id=str(account.service_id),
        protocol=account.protocol.value if hasattr(account.protocol, "value") else str(account.protocol),
        status=account.status.value if hasattr(account.status, "value") else str(account.status),
        public_key=account.public_key,
        password=account.password,
        assigned_ip=account.assigned_ip,
        dns_servers=account.dns_servers,
        allowed_ips=account.allowed_ips,
        bandwidth_limit_bytes=account.bandwidth_limit_bytes,
        bandwidth_used_bytes=int(account.total_bytes or 0),
        max_connections=account.max_connections,
        server_id=str(account.server_id) if account.server_id else None,
        provisioned_at=account.provisioned_at,
        last_handshake_at=account.last_handshake_at,
        client_config=account.client_config,
        notes=account.notes,
        created_at=account.created_at,
        updated_at=account.updated_at,
        protocol_configs=[
            VpnProtocolConfigSchema(
                id=str(pc.id),
                vpn_account_id=str(pc.vpn_account_id),
                config_key=pc.config_key,
                config_value=pc.config_value,
                created_at=pc.created_at,
                updated_at=pc.updated_at,
            )
            for pc in (account.protocol_configs or [])
        ],
        sessions=[
            VpnSessionSchema(
                id=str(s.id),
                vpn_account_id=str(s.vpn_account_id),
                status=s.status.value if hasattr(s.status, "value") else str(s.status),
                connected_at=s.connected_at,
                disconnected_at=s.disconnected_at,
                client_ip=s.client_ip,
                client_port=s.client_port,
                bytes_sent=int(s.bytes_sent or 0),
                bytes_received=int(s.bytes_received or 0),
                server_endpoint=s.server_endpoint,
                disconnect_reason=s.disconnect_reason,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in (account.sessions or [])
        ],
    )


def _build_server_response(server: VpnServer) -> VpnServerResponse:
    """Build a VpnServerResponse from a VpnServer model instance."""
    return VpnServerResponse(
        id=str(server.id),
        name=server.name,
        host=server.host,
        port=server.port,
        public_ip=server.public_ip,
        endpoint=server.endpoint,
        country=server.country,
        city=server.city,
        provider=server.provider,
        bandwidth_limit_mbps=server.bandwidth_limit_mbps,
        max_clients=server.max_clients,
        current_clients=server.current_clients or 0,
        is_active=server.is_active,
        created_at=server.created_at,
        updated_at=server.updated_at,
    )


def _require_admin(current_user: User) -> None:
    """Check if the authenticated user has admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )


def _generate_qr_base64(config_text: str) -> str | None:
    """Generate a QR code PNG as a base64-encoded string."""
    if qrcode is None:
        return None
    try:
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(config_text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


# ──────────────────────────────────────────────
# VPN Account Endpoints (Client & Admin)
# ──────────────────────────────────────────────


@router.post("/accounts", response_model=VpnAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_vpn_account(
    body: VpnAccountCreate,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpnAccountResponse:
    """
    Provision a new VPN account for a service.

    Creates protocol keys, assigns a server, and generates client config.
    Requires admin privileges.
    """
    _require_admin(current_user)

    try:
        account = await VpnAccountService.create_account(
            db=session,
            service_id=body.service_id,
            protocol=VpnProtocol(body.protocol),
            server_id=body.server_id,
            assigned_ip=body.assigned_ip,
            dns_servers=body.dns_servers,
            allowed_ips=body.allowed_ips,
            bandwidth_limit_bytes=body.bandwidth_limit_bytes,
            max_connections=body.max_connections,
            notes=body.notes,
        )
    except VpnProvisioningError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Reload with relationships for full response
    account = await VpnAccountService.get_account(session, str(account.id), load_relations=True)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account created but failed to reload",
        )
    return _build_account_response(account)


@router.get("/accounts", response_model=list[VpnAccountResponse])
async def list_vpn_accounts(
    service_id: str | None = Query(None, description="Filter by service UUID"),
    protocol: str | None = Query(None, description="Filter by protocol"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    server_id: str | None = Query(None, description="Filter by server UUID"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[VpnAccountResponse]:
    """
    List VPN accounts with optional filters.

    Admin: sees all accounts. Client: sees only their own services' accounts.
    """
    # Resolve protocol enum if provided
    protocol_enum: VpnProtocol | None = None
    if protocol:
        try:
            protocol_enum = VpnProtocol(protocol)
        except ValueError:
            protocol_enum = None

    # Resolve status enum if provided
    status_enum: VpnAccountStatus | None = None
    if status_filter:
        try:
            status_enum = VpnAccountStatus(status_filter)
        except ValueError:
            status_enum = None

    accounts, _ = await VpnAccountService.list_accounts(
        db=session,
        service_id=service_id,
        protocol=protocol_enum,
        status=status_enum,
        server_id=server_id,
        offset=offset,
        limit=limit,
    )

    # Non-admins can only see accounts tied to their own services
    if not current_user.is_admin:
        # Load services owned by this user
        from sqlalchemy import select

        user_services_stmt = select(Service.id).where(Service.user_id == str(current_user.id))
        result = await session.execute(user_services_stmt)
        user_service_ids = {str(row[0]) for row in result.all()}
        accounts = [a for a in accounts if str(a.service_id) in user_service_ids]

    return [_build_account_response(a) for a in accounts]


@router.get("/accounts/{account_id}", response_model=VpnAccountResponse)
async def get_vpn_account(
    account_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpnAccountResponse:
    """
    Get a single VPN account by ID with full details.
    """
    account = await VpnAccountService.get_account(session, account_id, load_relations=True)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VPN account not found",
        )

    # Non-admins can only access their own services' accounts
    if not current_user.is_admin:
        service = account.service
        if service is None or str(service.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    return _build_account_response(account)


@router.patch("/accounts/{account_id}", response_model=VpnAccountResponse)
async def update_vpn_account(
    account_id: str,
    body: VpnAccountUpdate,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpnAccountResponse:
    """
    Update a VPN account's settings.

    Allows changing protocol, status, IP, bandwidth limit, etc.
    Requires admin privileges for most fields.
    """
    _require_admin(current_user)

    account = await VpnAccountService.get_account(session, account_id, load_relations=False)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VPN account not found",
        )

    # Apply updates
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "protocol" and value is not None:
            setattr(account, field, VpnProtocol(value))
        elif field == "status" and value is not None:
            setattr(account, field, VpnAccountStatus(value))
        elif hasattr(account, field):
            setattr(account, field, value)

    from datetime import datetime, timezone

    account.updated_at = datetime.now(tz=timezone.utc)
    await session.commit()
    await session.refresh(account)

    # Reload with relations
    account = await VpnAccountService.get_account(session, account_id, load_relations=True)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reload account after update",
        )
    return _build_account_response(account)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vpn_account(
    account_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> None:
    """
    Terminate and delete a VPN account.

    Removes peer from server, marks service appropriately.
    Requires admin privileges.
    """
    _require_admin(current_user)

    account = await VpnAccountService.get_account(session, account_id, load_relations=False)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VPN account not found",
        )

    await VpnAccountService.terminate_account(session, account)


# ──────────────────────────────────────────────
# VPN Account Actions (Suspend / Unsuspend)
# ──────────────────────────────────────────────


@router.post("/accounts/{account_id}/suspend", response_model=VpnAccountResponse)
async def suspend_vpn_account(
    account_id: str,
    reason: str = Query("manual", description="Suspension reason"),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpnAccountResponse:
    """
    Suspend a VPN account (stops traffic, ends sessions).
    Requires admin privileges.
    """
    _require_admin(current_user)

    account = await VpnAccountService.get_account(session, account_id, load_relations=True)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VPN account not found",
        )

    try:
        account = await VpnAccountService.suspend_account(session, account, reason=reason)
    except VpnServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Reload
    account = await VpnAccountService.get_account(session, account_id, load_relations=True)
    if account is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reload")
    return _build_account_response(account)


@router.post("/accounts/{account_id}/unsuspend", response_model=VpnAccountResponse)
async def unsuspend_vpn_account(
    account_id: str,
    reason: str = Query("manual", description="Re-activation reason"),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpnAccountResponse:
    """
    Re-activate a suspended VPN account.
    Requires admin privileges.
    """
    _require_admin(current_user)

    account = await VpnAccountService.get_account(session, account_id, load_relations=True)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VPN account not found",
        )

    try:
        account = await VpnAccountService.unsuspend_account(session, account, reason=reason)
    except VpnServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    account = await VpnAccountService.get_account(session, account_id, load_relations=True)
    if account is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reload")
    return _build_account_response(account)


# ──────────────────────────────────────────────
# VPN Configuration Download
# ──────────────────────────────────────────────


@router.get("/accounts/{account_id}/config", response_model=VpnConfigResponse)
async def get_vpn_config(
    account_id: str,
    include_qr: bool = Query(False, description="Include QR code as base64 PNG"),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpnConfigResponse:
    """
    Download VPN client configuration for a specific account.

    Returns the config text and optionally a QR code.
    Accessible to the service owner or admin.
    """
    account = await VpnAccountService.get_account(session, account_id, load_relations=False)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VPN account not found",
        )

    # Check ownership
    if not current_user.is_admin:
        service = account.service
        if service is None or str(service.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    config_text = account.client_config
    if config_text is None:
        # Try to regenerate
        try:
            config_text = await VpnAccountService.build_client_config_text(session, account)
        except VpnConfigGenerationError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Config generation failed: {exc}",
            ) from exc

    qr_base64: str | None = None
    if include_qr and config_text:
        qr_base64 = _generate_qr_base64(config_text)

    return VpnConfigResponse(
        account_id=str(account.id),
        protocol=account.protocol.value if hasattr(account.protocol, "value") else str(account.protocol),
        config_text=config_text,
        config_qr_base64=qr_base64,
    )


# ──────────────────────────────────────────────
# VPN Traffic / Usage Endpoints
# ──────────────────────────────────────────────


@router.get("/accounts/{account_id}/traffic", response_model=VpnTrafficResponse)
async def get_vpn_traffic(
    account_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpnTrafficResponse:
    """
    Get traffic usage for a specific VPN account.

    Returns bytes sent/received, bandwidth limits, and session info.
    """
    account = await VpnAccountService.get_account(session, account_id, load_relations=True)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VPN account not found",
        )

    # Check ownership
    if not current_user.is_admin:
        service = account.service
        if service is None or str(service.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    summary = await VpnAccountService.get_traffic_summary(session, account)
    return _build_traffic_response(account, summary)


def _build_traffic_response(account: VpnAccount, summary: AccountTrafficSummary) -> VpnTrafficResponse:
    """Build a VpnTrafficResponse from account and traffic summary."""
    from modules.vpn.schemas import VpnUsageSummary

    total_bytes = summary.bytes_sent + summary.bytes_received
    bandwidth_remaining: int | None = None
    bandwidth_used_percent: float | None = None

    if account.bandwidth_limit_bytes:
        bandwidth_remaining = max(0, account.bandwidth_limit_bytes - total_bytes)
        if account.bandwidth_limit_bytes > 0:
            bandwidth_used_percent = round((total_bytes / account.bandwidth_limit_bytes) * 100, 2)

    usage = VpnUsageSummary(
        total_bytes_sent=summary.bytes_sent,
        total_bytes_received=summary.bytes_received,
        total_bytes=total_bytes,
        bandwidth_limit_bytes=account.bandwidth_limit_bytes,
        bandwidth_remaining_bytes=bandwidth_remaining,
        bandwidth_used_percent=bandwidth_used_percent,
        current_sessions=summary.active_sessions,
        last_handshake_at=summary.last_handshake,
    )

    return VpnTrafficResponse(
        account_id=str(account.id),
        protocol=account.protocol.value if hasattr(account.protocol, "value") else str(account.protocol),
        status=account.status.value if hasattr(account.status, "value") else str(account.status),
        usage=usage,
    )


# ──────────────────────────────────────────────
# VPN Services (User-facing list)
# ──────────────────────────────────────────────


@router.get("/services", response_model=VpnServiceListResponse)
async def list_my_vpn_services(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpnServiceListResponse:
    """
    List the current user's VPN services with associated accounts and status.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    # Find active services owned by the user
    stmt = (
        select(Service)
        .options(selectinload(Service.vpn_accounts))
        .where(
            Service.user_id == str(current_user.id),
            Service.status.in_([ServiceStatus.ACTIVE, ServiceStatus.SUSPENDED]),
        )
        .order_by(Service.created_at.desc())
    )
    result = await session.execute(stmt)
    services = result.scalars().all()

    items: list[VpnServiceListItem] = []
    for svc in services:
        for acc in svc.vpn_accounts or []:
            items.append(
                VpnServiceListItem(
                    service_id=str(svc.id),
                    account_id=str(acc.id) if acc else None,
                    protocol=acc.protocol.value if acc and hasattr(acc.protocol, "value") else None,
                    status=acc.status.value if acc and hasattr(acc.status, "value") else str(svc.status.value),
                    assigned_ip=acc.assigned_ip if acc else None,
                    bandwidth_used_bytes=int(acc.total_bytes or 0) if acc else 0,
                    bandwidth_limit_bytes=acc.bandwidth_limit_bytes if acc else None,
                    expires_at=svc.expires_at,
                    provisioned_at=acc.provisioned_at if acc else None,
                    last_handshake_at=acc.last_handshake_at if acc else None,
                )
            )
        # If service has no accounts yet, still show the service
        if not svc.vpn_accounts:
            items.append(
                VpnServiceListItem(
                    service_id=str(svc.id),
                    account_id=None,
                    protocol=None,
                    status=str(svc.status.value),
                    assigned_ip=None,
                    bandwidth_used_bytes=0,
                    bandwidth_limit_bytes=None,
                    expires_at=svc.expires_at,
                    provisioned_at=None,
                    last_handshake_at=None,
                )
            )

    return VpnServiceListResponse(services=items, total=len(items))


# ──────────────────────────────────────────────
# VPN Server Management (Admin)
# ──────────────────────────────────────────────


@router.post("/servers", response_model=VpnServerResponse, status_code=status.HTTP_201_CREATED)
async def create_vpn_server(
    body: VpnServerCreate,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpnServerResponse:
    """
    Register a new VPN server.
    Requires admin privileges.
    """
    _require_admin(current_user)

    server = await VpnServerService.create_server(
        db=session,
        name=body.name,
        host=body.host,
        port=body.port,
        public_ip=body.public_ip,
        private_key=body.private_key,
        public_key=body.public_key,
        endpoint=body.endpoint,
        country=body.country,
        city=body.city,
        provider=body.provider,
        bandwidth_limit_mbps=body.bandwidth_limit_mbps,
        max_clients=body.max_clients,
        is_active=body.is_active,
    )
    return _build_server_response(server)


@router.get("/servers", response_model=list[VpnServerResponse])
async def list_vpn_servers(
    include_inactive: bool = Query(False, description="Include inactive servers"),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[VpnServerResponse]:
    """
    List all VPN servers.
    """
    servers = await VpnServerService.list_servers(
        db=session,
        include_inactive=include_inactive or current_user.is_admin,
    )
    return [_build_server_response(s) for s in servers]


@router.get("/servers/{server_id}", response_model=VpnServerResponse)
async def get_vpn_server(
    server_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpnServerResponse:
    """
    Get details of a specific VPN server.
    """
    server = await VpnServerService.get_server(session, server_id)
    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VPN server not found",
        )
    return _build_server_response(server)


@router.patch("/servers/{server_id}", response_model=VpnServerResponse)
async def update_vpn_server(
    server_id: str,
    body: VpnServerUpdate,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpnServerResponse:
    """
    Update a VPN server's configuration.
    Requires admin privileges.
    """
    _require_admin(current_user)

    server = await VpnServerService.get_server(session, server_id)
    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VPN server not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(server, field):
            setattr(server, field, value)

    from datetime import datetime, timezone

    server.updated_at = datetime.now(tz=timezone.utc)
    await session.commit()
    await session.refresh(server)
    return _build_server_response(server)


@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vpn_server(
    server_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> None:
    """
    Remove a VPN server registration.
    Requires admin privileges.
    """
    _require_admin(current_user)

    server = await VpnServerService.get_server(session, server_id)
    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VPN server not found",
        )

    await VpnServerService.delete_server(session, server)


# ──────────────────────────────────────────────
# VPN Products (Client-facing)
# ──────────────────────────────────────────────


@router.get("/products", response_model=list[VpnProductResponse])
async def list_vpn_products(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[VpnProductResponse]:
    """
    List available VPN products for purchase.
    """
    from sqlalchemy import select

    from shared.models.product import Product

    stmt = select(Product).where(
        Product.module == "vpn",
        Product.is_active.is_(True),
    )
    result = await session.execute(stmt)
    products = result.scalars().all()

    return [
        VpnProductResponse(
            id=str(p.id),
            name=p.name,
            description=p.description,
            protocols=p.features.get("protocols", ["wireguard"]) if p.features else ["wireguard"],
            bandwidth=p.features.get("bandwidth") if p.features else None,
            speed=p.features.get("speed") if p.features else None,
            price_monthly=float(p.price_monthly) if p.price_monthly else None,
            price_quarterly=float(p.price_quarterly) if p.price_quarterly else None,
            price_semi_annually=float(p.price_semi_annually) if p.price_semi_annually else None,
            price_annually=float(p.price_annually) if p.price_annually else None,
            is_active=p.is_active,
        )
        for p in products
    ]


# ──────────────────────────────────────────────
# VPN Purchase (Client-facing)
# ──────────────────────────────────────────────


@router.post("/purchase", response_model=VpnPurchaseResponse)
async def purchase_vpn(
    body: VpnPurchaseRequest,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpnPurchaseResponse:
    """
    Initiate a VPN purchase. Creates an invoice and returns a payment URL.

    This is the client-facing purchase flow. After payment confirmation
    via webhook, the account will be provisioned automatically.
    """
    from modules.vpn.services import VpnPurchaseProcessor

    try:
        result = await VpnPurchaseProcessor.process_purchase(
            db=session,
            user=current_user,
            product_id=body.product_id,
            protocol=body.protocol,
            server_id=body.server_id,
            billing_cycle=body.billing_cycle,
        )
    except VpnServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return VpnPurchaseResponse(
        payment_url=result.get("payment_url"),
        invoice_id=result.get("invoice_id"),
        service_id=result.get("service_id"),
        message=result.get("message", "Purchase initiated"),
    )


__all__ = ["router"]