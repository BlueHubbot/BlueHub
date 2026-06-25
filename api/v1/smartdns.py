"""
BlueHub SmartDNS API Endpoints
===============================
FastAPI router for SmartDNS profile and DNS record management.
Provides admin and client-facing endpoints for DNS profile CRUD,
record management, sync operations, and status monitoring.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.auth import get_current_user
from dependencies.db import get_async_session
from modules.smartdns.schemas import (
    DnsRecordCreate,
    DnsRecordResponse,
    DnsRecordUpdate,
    SmartDnsProfileCreate,
    SmartDnsProfileResponse,
    SmartDnsProfileSummary,
    SmartDnsProfileUpdate,
    SmartDnsStatusResponse,
    SmartDnsSyncResponse,
)
from modules.smartdns.services import (
    ProfileAlreadyExistsError,
    ProfileNotFoundError,
    RecordNotFoundError,
    RecordValidationError,
    SmartDnsError,
    SmartDnsService,
    build_profile_response,
    build_record_response,
)
from shared.models.user import User

router = APIRouter(prefix="/smartdns", tags=["SmartDNS"])


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


# ──────────────────────────────────────────────
# Profile Endpoints
# ──────────────────────────────────────────────


@router.post(
    "/profiles",
    response_model=SmartDnsProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create SmartDNS Profile",
)
async def create_profile(
    payload: SmartDnsProfileCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> SmartDnsProfileResponse:
    """Provision a new SmartDNS profile for a billing service."""
    _require_admin(current_user)

    service = SmartDnsService(db)
    try:
        profile = await service.create_profile(
            service_id=payload.service_id,
            profile_name=payload.profile_name,
            upstream_dns=payload.upstream_dns,
            geo_region=payload.geo_region,
            allowed_ips=payload.allowed_ips,
            max_queries_per_second=payload.max_queries_per_second,
            enable_dnssec=payload.enable_dnssec,
            enable_logging=payload.enable_logging,
            enable_ad_blocking=payload.enable_ad_blocking,
            extra_config=payload.extra_config,
            notes=payload.notes,
        )
        return build_profile_response(profile)
    except ProfileAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SmartDnsError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


@router.get(
    "/profiles",
    response_model=list[SmartDnsProfileSummary],
    summary="List SmartDNS Profiles",
)
async def list_profiles(
    status_filter: str | None = Query(None, alias="status"),
    geo_region: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[SmartDnsProfileSummary]:
    """List SmartDNS profiles with optional status and region filters."""
    _require_admin(current_user)

    service = SmartDnsService(db)
    profiles = await service.list_profiles(
        status=status_filter,
        geo_region=geo_region,
        offset=offset,
        limit=limit,
    )
    return [
        SmartDnsProfileSummary(
            id=p.id,
            service_id=p.service_id,
            profile_name=p.profile_name,
            status=p.status,
            geo_region=p.geo_region,
            pdns_zone_name=p.pdns_zone_name,
            total_queries=p.total_queries or 0,
            created_at=p.created_at,
        )
        for p in profiles
    ]


@router.get(
    "/profiles/{profile_id}",
    response_model=SmartDnsProfileResponse,
    summary="Get SmartDNS Profile",
)
async def get_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> SmartDnsProfileResponse:
    """Get a SmartDNS profile by ID."""
    service = SmartDnsService(db)
    try:
        profile = await service.get_profile(profile_id)
        return build_profile_response(profile)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch(
    "/profiles/{profile_id}",
    response_model=SmartDnsProfileResponse,
    summary="Update SmartDNS Profile",
)
async def update_profile(
    profile_id: UUID,
    payload: SmartDnsProfileUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> SmartDnsProfileResponse:
    """Update a SmartDNS profile's configuration."""
    _require_admin(current_user)

    service = SmartDnsService(db)
    try:
        profile = await service.update_profile(profile_id, payload)
        return build_profile_response(profile)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete SmartDNS Profile",
)
async def delete_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a SmartDNS profile and all its DNS records."""
    _require_admin(current_user)

    service = SmartDnsService(db)
    try:
        await service.delete_profile(profile_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get(
    "/profiles/{profile_id}/status",
    response_model=SmartDnsStatusResponse,
    summary="Get SmartDNS Profile Status",
)
async def get_profile_status(
    profile_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> SmartDnsStatusResponse:
    """Get detailed status information for a SmartDNS profile."""
    service = SmartDnsService(db)
    try:
        return await service.get_profile_status(profile_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ──────────────────────────────────────────────
# DNS Record Endpoints
# ──────────────────────────────────────────────


@router.post(
    "/profiles/{profile_id}/records",
    response_model=DnsRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add DNS Record",
)
async def add_record(
    profile_id: UUID,
    payload: DnsRecordCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> DnsRecordResponse:
    """Add a DNS record to a SmartDNS profile."""
    _require_admin(current_user)

    service = SmartDnsService(db)
    try:
        record = await service.add_record(profile_id, payload)
        return build_record_response(record)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RecordValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )


@router.get(
    "/profiles/{profile_id}/records",
    response_model=list[DnsRecordResponse],
    summary="List DNS Records",
)
async def list_records(
    profile_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[DnsRecordResponse]:
    """List DNS records for a SmartDNS profile."""
    service = SmartDnsService(db)
    try:
        records = await service.list_records(profile_id, offset, limit)
        return [build_record_response(r) for r in records]
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch(
    "/profiles/records/{record_id}",
    response_model=DnsRecordResponse,
    summary="Update DNS Record",
)
async def update_record(
    record_id: UUID,
    payload: DnsRecordUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> DnsRecordResponse:
    """Update a DNS record's configuration."""
    _require_admin(current_user)

    service = SmartDnsService(db)
    try:
        record = await service.update_record(record_id, payload)
        return build_record_response(record)
    except RecordNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/profiles/records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete DNS Record",
)
async def delete_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a DNS record from a SmartDNS profile."""
    _require_admin(current_user)

    service = SmartDnsService(db)
    try:
        await service.delete_record(record_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except RecordNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ──────────────────────────────────────────────
# Sync Endpoint
# ──────────────────────────────────────────────


@router.post(
    "/profiles/{profile_id}/sync",
    response_model=SmartDnsSyncResponse,
    summary="Sync DNS Records with PowerDNS",
)
async def sync_records(
    profile_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> SmartDnsSyncResponse:
    """Sync all unsynced DNS records for a profile with PowerDNS."""
    _require_admin(current_user)

    service = SmartDnsService(db)
    try:
        return await service.sync_records(profile_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


__all__ = ["router"]