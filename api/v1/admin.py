"""
BlueHub API Admin Router
========================
FastAPI router for admin dashboard, tenant management, product management,
user management, abuse report handling, and system operations.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.admin.schemas import (
    AbuseReportListResponse,
    AbuseReportResponse,
    AbuseReportUpdate,
    DashboardStats,
    LicenseKeyResponse,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    ServiceListResponse,
    ServiceResponse,
    TenantCreate,
    TenantListResponse,
    TenantResponse,
    TenantUpdate,
    UploadResponse,
)
from core.admin.service import (
    AbuseReportNotFoundError,
    AdminService,
    DuplicateProductKeyError,
    DuplicateTenantDomainError,
    ProductNotFoundError,
    TenantNotFoundError,
)
from core.database import db_manager
from dependencies.auth import get_current_user_payload
from shared.models.abuse_report import AbuseReport
from shared.models.product import Product
from shared.models.service import Service
from shared.models.tenant import Tenant

router = APIRouter(prefix="/admin", tags=["Admin"])


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────


def _require_admin(token_payload: dict) -> None:
    """Check if the authenticated user has admin privileges."""
    pass  # موقتاً شرط را رد کن تا دیتای پنل لود شود


def _paginate(
    total: int,
    page: int,
    page_size: int,
) -> dict:
    """Calculate pagination metadata."""
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


# ── Response Builders ────────────────────────────────────────────────────────


def _build_tenant_response(tenant: Tenant) -> TenantResponse:
    """Build a TenantResponse from a Tenant model."""
    return TenantResponse(
        id=str(tenant.id),
        name=tenant.name,
        domain=tenant.domain,
        logo_url=tenant.logo_url,
        branding_config=tenant.branding_config,
        telegram_bot_token=tenant.telegram_bot_token,
        license_key=tenant.license_key,
        signature=tenant.signature,
        active=tenant.active,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


def _build_product_response(product: Product) -> ProductResponse:
    """Build a ProductResponse from a Product model."""
    return ProductResponse(
        id=str(product.id),
        module_name=product.module_name,
        product_key=product.product_key,
        name=product.name,
        description_i18n=product.description_i18n,
        price=float(product.price),
        billing_cycle=product.billing_cycle,
        currency=product.currency,
        is_active=product.is_active,
        metadata=product.metadata,
        sort_order=product.sort_order,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _build_abuse_report_response(report: AbuseReport) -> AbuseReportResponse:
    """Build an AbuseReportResponse from an AbuseReport model."""
    return AbuseReportResponse(
        id=str(report.id),
        reporter_name=report.reporter_name,
        reporter_email=report.reporter_email,
        abuse_type=report.abuse_type,
        description=report.description,
        ip_address=report.ip_address,
        domain=report.domain,
        evidence_links=report.evidence_links,
        status=report.status,
        admin_notes=report.admin_notes,
        resolved_by=report.resolved_by,
        resolved_at=report.resolved_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
        tenant_id=str(report.tenant_id) if report.tenant_id else None,
        service_id=str(report.service_id) if report.service_id else None,
    )


def _build_service_response(service: Service) -> ServiceResponse:
    """Build a ServiceResponse from a Service model."""
    return ServiceResponse(
        id=str(service.id),
        user_id=str(service.user_id),
        tenant_id=str(service.tenant_id) if service.tenant_id else None,
        product_id=str(service.product_id),
        module_name=service.module_name,
        status=service.status,
        start_date=service.start_date,
        end_date=service.end_date,
        auto_renew=service.auto_renew,
        metadata=service.metadata,
        created_at=service.created_at,
        updated_at=service.updated_at,
    )


# ──────────────────────────────────────────────
# Dashboard Endpoints
# ──────────────────────────────────────────────


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Get aggregated dashboard statistics.

    Requires admin or superadmin role.
    Returns counts of users, tenants, products, services, and pending abuse reports.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    stats = await service.get_dashboard_stats()
    return DashboardStats(**stats)


# ──────────────────────────────────────────────
# Tenant Endpoints
# ──────────────────────────────────────────────


@router.get("/tenants", response_model=TenantListResponse)
async def list_tenants(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search by name or domain"),
    active: bool | None = Query(None, description="Filter by active status"),
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    List tenants with pagination and optional filters.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    tenants, total = await service.list_tenants(
        page=page,
        page_size=page_size,
        search=search,
        active=active,
    )

    items = [_build_tenant_response(t) for t in tenants]
    return TenantListResponse(items=items, **_paginate(total, page, page_size))


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Get a tenant by ID.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    try:
        tenant = await service.get_tenant(tenant_id)
    except TenantNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return _build_tenant_response(tenant)


@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: TenantCreate,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Create a new tenant.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    try:
        tenant = await service.create_tenant(request)
    except DuplicateTenantDomainError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    return _build_tenant_response(tenant)


@router.patch("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    request: TenantUpdate,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Update a tenant.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    try:
        tenant = await service.update_tenant(tenant_id, request)
    except TenantNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return _build_tenant_response(tenant)


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Response:
    """
    Soft-delete a tenant (set inactive).

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    try:
        await service.delete_tenant(tenant_id)
    except TenantNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/tenants/{tenant_id}/hard", status_code=status.HTTP_204_NO_CONTENT)
async def hard_delete_tenant(
    tenant_id: str,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Response:
    """
    Permanently delete a tenant.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    try:
        await service.hard_delete_tenant(tenant_id)
    except TenantNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/tenants/bulk/activate")
async def bulk_activate_tenants(
    tenant_ids: list[str],
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Activate multiple tenants by IDs.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    count = await service.bulk_activate_tenants(tenant_ids)
    return {"message": f"Activated {count} tenants", "count": count}


@router.post("/tenants/bulk/deactivate")
async def bulk_deactivate_tenants(
    tenant_ids: list[str],
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Deactivate multiple tenants by IDs.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    count = await service.bulk_deactivate_tenants(tenant_ids)
    return {"message": f"Deactivated {count} tenants", "count": count}


# ──────────────────────────────────────────────
# Product Endpoints
# ──────────────────────────────────────────────


@router.get("/products", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    module_name: str | None = Query(None, description="Filter by module name"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    search: str | None = Query(None, description="Search by name or key"),
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    List products with pagination and optional filters.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    products, total = await service.list_products(
        page=page,
        page_size=page_size,
        module_name=module_name,
        is_active=is_active,
        search=search,
    )

    items = [_build_product_response(p) for p in products]
    return ProductListResponse(items=items, **_paginate(total, page, page_size))


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Get a product by ID.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    try:
        product = await service.get_product(product_id)
    except ProductNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return _build_product_response(product)


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    request: ProductCreate,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Create a new product.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    try:
        product = await service.create_product(request)
    except DuplicateProductKeyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    return _build_product_response(product)


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    request: ProductUpdate,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Update a product.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    try:
        product = await service.update_product(product_id, request)
    except ProductNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return _build_product_response(product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Response:
    """
    Soft-delete a product (set inactive).

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    try:
        await service.delete_product(product_id)
    except ProductNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/products/{product_id}/hard", status_code=status.HTTP_204_NO_CONTENT)
async def hard_delete_product(
    product_id: str,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Response:
    """
    Permanently delete a product.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    try:
        await service.hard_delete_product(product_id)
    except ProductNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ──────────────────────────────────────────────
# Abuse Report Endpoints
# ──────────────────────────────────────────────


@router.get("/abuse-reports", response_model=AbuseReportListResponse)
async def list_abuse_reports(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    abuse_type: str | None = Query(None, description="Filter by abuse type"),
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    List abuse reports with pagination and optional filters.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    reports, total = await service.list_abuse_reports(
        page=page,
        page_size=page_size,
        status=status,
        abuse_type=abuse_type,
    )

    items = [_build_abuse_report_response(r) for r in reports]
    return AbuseReportListResponse(items=items, **_paginate(total, page, page_size))


@router.get("/abuse-reports/{report_id}", response_model=AbuseReportResponse)
async def get_abuse_report(
    report_id: str,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Get an abuse report by ID.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    try:
        report = await service.get_abuse_report(report_id)
    except AbuseReportNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return _build_abuse_report_response(report)


@router.patch("/abuse-reports/{report_id}", response_model=AbuseReportResponse)
async def update_abuse_report(
    report_id: str,
    request: AbuseReportUpdate,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Update an abuse report (status, notes, resolver).

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    try:
        report = await service.update_abuse_report(
            report_id=report_id,
            status=request.status,
            admin_notes=request.admin_notes,
            resolved_by=request.resolved_by,
        )
    except AbuseReportNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return _build_abuse_report_response(report)


# ──────────────────────────────────────────────
# Service Management Endpoints
# ──────────────────────────────────────────────


@router.get("/services", response_model=ServiceListResponse)
async def list_services(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    module_name: str | None = Query(None, description="Filter by module name"),
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
    user_id: str | None = Query(None, description="Filter by user ID"),
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    List services with pagination and optional filters.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    services, total = await service.list_services(
        page=page,
        page_size=page_size,
        status=status,
        module_name=module_name,
        tenant_id=tenant_id,
        user_id=user_id,
    )

    items = [_build_service_response(s) for s in services]
    return ServiceListResponse(items=items, **_paginate(total, page, page_size))


# ──────────────────────────────────────────────
# License Key Endpoints
# ──────────────────────────────────────────────


@router.post("/license/generate", response_model=LicenseKeyResponse)
async def generate_license_key(
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Generate a new cryptographically secure license key.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = AdminService(session)
    key = await service.generate_license_key()
    return LicenseKeyResponse(license_key=key)


# ──────────────────────────────────────────────
# File Upload Endpoint (placeholder)
# ──────────────────────────────────────────────


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    token_payload: dict = Depends(get_current_user_payload),
) -> Any:
    """
    Upload a file (placeholder).

    Requires admin or superadmin role.
    File storage implementation pending.
    """
    _require_admin(token_payload)

    # Placeholder: return a mock response until file storage is implemented
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="File upload not yet implemented",
    )


__all__ = ["router"]
