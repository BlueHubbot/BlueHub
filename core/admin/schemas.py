"""
BlueHub Admin Schemas
======================
Pydantic schemas for admin dashboard, tenant, product,
user management, and abuse report endpoints.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ── Dashboard Stats ──────────────────────────────────────────────────────────


class DashboardStats(BaseModel):
    """Schema for admin dashboard statistics."""

    total_users: int = 0
    active_users: int = 0
    total_tenants: int = 0
    active_tenants: int = 0
    total_products: int = 0
    total_services: int = 0
    active_services: int = 0
    pending_abuse_reports: int = 0
    total_revenue: float = 0.0
    revenue_this_month: float = 0.0


# ── Tenant Schemas ───────────────────────────────────────────────────────────


class TenantCreate(BaseModel):
    """Schema for creating a new tenant."""

    name: str = Field(..., min_length=1, max_length=255)
    domain: str = Field(..., min_length=1, max_length=255)
    logo_url: str | None = Field(None, max_length=512)
    branding_config: dict | None = Field(None)
    telegram_bot_token: str | None = Field(None, max_length=255)
    license_key: str = Field(..., min_length=1, max_length=255)
    signature: str | None = Field(None)
    active: bool = True


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""

    name: str | None = Field(None, min_length=1, max_length=255)
    domain: str | None = Field(None, min_length=1, max_length=255)
    logo_url: str | None = Field(None, max_length=512)
    branding_config: dict | None = Field(None)
    telegram_bot_token: str | None = Field(None, max_length=255)
    signature: str | None = Field(None)
    active: bool | None = None


class TenantResponse(BaseModel):
    """Schema for tenant response."""

    id: str
    name: str
    domain: str
    logo_url: str | None = None
    branding_config: dict | None = None
    telegram_bot_token: str | None = None
    license_key: str
    signature: str | None = None
    active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class TenantListResponse(BaseModel):
    """Schema for paginated tenant list."""

    items: list[TenantResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Product Schemas (Admin) ─────────────────────────────────────────────────


class ProductCreate(BaseModel):
    """Schema for creating a new product."""

    module_name: str = Field(..., max_length=50)
    product_key: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    description_i18n: dict | None = Field(None)
    price: float = Field(..., ge=0)
    billing_cycle: str = Field("monthly", max_length=20)
    currency: str = Field("USD", max_length=3)
    is_active: bool = True
    metadata: dict | None = Field(None)
    sort_order: int = 0


class ProductUpdate(BaseModel):
    """Schema for updating a product."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description_i18n: dict | None = Field(None)
    price: float | None = Field(None, ge=0)
    billing_cycle: str | None = Field(None, max_length=20)
    currency: str | None = Field(None, max_length=3)
    is_active: bool | None = None
    metadata: dict | None = Field(None)
    sort_order: int | None = None


class ProductResponse(BaseModel):
    """Schema for product response."""

    id: str
    module_name: str
    product_key: str
    name: str
    description_i18n: dict | None = None
    price: float
    billing_cycle: str
    currency: str
    is_active: bool
    metadata: dict | None = None
    sort_order: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    """Schema for paginated product list."""

    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Abuse Report Schemas ────────────────────────────────────────────────────


class AbuseReportUpdate(BaseModel):
    """Schema for updating an abuse report."""

    status: str = Field(..., max_length=20)
    admin_notes: str | None = Field(None)
    resolved_by: str | None = Field(None, max_length=255)


class AbuseReportResponse(BaseModel):
    """Schema for abuse report response."""

    id: str
    reporter_name: str | None = None
    reporter_email: str | None = None
    abuse_type: str
    description: str
    ip_address: str | None = None
    domain: str | None = None
    evidence_links: list[str] | None = None
    status: str
    admin_notes: str | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    tenant_id: str | None = None
    service_id: str | None = None

    model_config = {"from_attributes": True}


class AbuseReportListResponse(BaseModel):
    """Schema for paginated abuse report list."""

    items: list[AbuseReportResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Upload Response ─────────────────────────────────────────────────────────


class UploadResponse(BaseModel):
    """Schema for file upload response."""

    url: str
    filename: str
    size: int
    content_type: str


class LicenseKeyResponse(BaseModel):
    """Schema for generated license key."""

    license_key: str


# ── Service Summary ─────────────────────────────────────────────────────────


class ServiceResponse(BaseModel):
    """Schema for service summary response."""

    id: str
    user_id: str
    tenant_id: str | None = None
    product_id: str
    module_name: str
    status: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    auto_renew: bool = True
    metadata: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ServiceListResponse(BaseModel):
    """Schema for paginated service list."""

    items: list[ServiceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


__all__ = [
    "AbuseReportListResponse",
    "AbuseReportResponse",
    "AbuseReportUpdate",
    "DashboardStats",
    "LicenseKeyResponse",
    "ProductCreate",
    "ProductListResponse",
    "ProductResponse",
    "ProductUpdate",
    "ServiceListResponse",
    "ServiceResponse",
    "TenantCreate",
    "TenantListResponse",
    "TenantResponse",
    "TenantUpdate",
    "UploadResponse",
]
