"""
BlueHub Tenant Public API Router
=================================
FastAPI router for authenticated tenant self-service endpoints.
Provides current tenant's branding/white-label configuration.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import db_manager
from dependencies.auth import get_current_user
from shared.models.tenant import Tenant
from shared.models.user import User

router = APIRouter(prefix="/tenants", tags=["Tenants"])


class TenantBrandingResponse:
    """Response schema for current tenant branding.

    Defined inline to match the interface expected by the
    web client white-label components (use-tenant.ts).
    """

    def __init__(
        self,
        *,
        logo_url: str | None,
        favicon_url: str | None,
        primary_color: str | None,
        secondary_color: str | None,
        accent_color: str | None,
        page_title: str | None,
        company_name: str | None,
    ) -> None:
        self.logo_url = logo_url
        self.favicon_url = favicon_url
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.accent_color = accent_color
        self.page_title = page_title
        self.company_name = company_name


@router.get(
    "/current",
    summary="Get current tenant branding",
    description="Returns branding/white-label config for the authenticated user's tenant.",
    response_model=None,  # plain dict response for flexibility
)
async def get_current_tenant_branding(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(db_manager.get_async_session),
):
    """
    Return the current tenant's branding configuration for
    white-label rendering in the web client.

    The authenticated user's tenant_id is used to look up
    the tenant record. Branding fields are extracted from
    the tenant's ``branding_config`` JSONB column (for colors)
    and direct columns (logo_url, name).

    Returns a flat JSON object compatible with the
    ``TenantBranding`` interface in ``use-tenant.ts``.
    """
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any tenant",
        )

    result = await session.execute(
        select(Tenant).where(Tenant.id == str(tenant_id))
    )
    tenant = result.scalars().first()

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Extract branding_config fields with safe defaults
    branding = tenant.branding_config or {}

    response = {
        "logo_url": tenant.logo_url,
        "favicon_url": branding.get("favicon_url"),
        "primary_color": branding.get("primary_color"),
        "secondary_color": branding.get("secondary_color"),
        "accent_color": branding.get("accent_color", branding.get("secondary_color")),
        "page_title": branding.get("page_title", tenant.name),
        "company_name": tenant.name,
    }

    return response


__all__ = ["router"]
