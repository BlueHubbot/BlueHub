"""
BlueHub Billing API Router
===========================
API endpoints for billing operations including wallet management,
invoice processing, transactions, product catalog, tenant pricing,
and commission tracking.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.billing import BillingService
from core.billing.schemas import (
    BillingSummaryResponse,
    CommissionListResponse,
    CommissionResponse,
    CreateInvoiceRequest,
    CreateProductRequest,
    InvoiceListResponse,
    InvoiceResponse,
    MarkCommissionPaidRequest,
    ProductListResponse,
    ProductResponse,
    RevenueReportResponse,
    SetTenantPricingRequest,
    TenantPricingResponse,
    TransactionListResponse,
    TransactionResponse,
    WalletBalanceResponse,
    WalletDeductRequest,
    WalletTopUpRequest,
)
from dependencies import get_current_user_payload
from dependencies.db import get_async_session

router = APIRouter(prefix="/billing", tags=["Billing"])

# ── Helper ─────────────────────────────────────────────────────────────────


async def _get_billing_service(
    session: AsyncSession = Depends(get_async_session),
) -> BillingService:
    """Dependency provider for BillingService."""
    return BillingService(session=session)


# ── Wallet Endpoints ───────────────────────────────────────────────────────


@router.get(
    "/wallet/balance",
    response_model=WalletBalanceResponse,
    summary="Get wallet balance",
    description="Retrieve the current wallet balance for the authenticated user.",
)
async def get_wallet_balance(
    user_payload: dict = Depends(get_current_user_payload),
    service: BillingService = Depends(_get_billing_service),
):
    """Get wallet balance for the current user."""
    user_id = user_payload["sub"]
    result = await service.get_wallet_balance(user_id)
    return WalletBalanceResponse(**result)


@router.post(
    "/wallet/top-up",
    response_model=WalletBalanceResponse,
    summary="Top up wallet",
    description="Add funds to the authenticated user's wallet.",
)
async def top_up_wallet(
    request: WalletTopUpRequest,
    user_payload: dict = Depends(get_current_user_payload),
    service: BillingService = Depends(_get_billing_service),
):
    """Add funds to the current user's wallet."""
    user_id = user_payload["sub"]
    result = await service.top_up_wallet(user_id, request)
    return WalletBalanceResponse(**result)


@router.post(
    "/wallet/deduct",
    response_model=WalletBalanceResponse,
    summary="Deduct from wallet",
    description="Deduct funds from the authenticated user's wallet.",
)
async def deduct_wallet(
    request: WalletDeductRequest,
    user_payload: dict = Depends(get_current_user_payload),
    service: BillingService = Depends(_get_billing_service),
):
    """Deduct funds from the current user's wallet."""
    user_id = user_payload["sub"]
    result = await service.deduct_wallet(user_id, request)
    return WalletBalanceResponse(**result)


# ── Transaction Endpoints ──────────────────────────────────────────────────


@router.get(
    "/transactions",
    response_model=TransactionListResponse,
    summary="List transactions",
    description="List transactions for the authenticated user with pagination.",
)
async def list_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    transaction_type: str | None = Query(
        None, description="Filter by transaction type"
    ),
    user_payload: dict = Depends(get_current_user_payload),
    service: BillingService = Depends(_get_billing_service),
):
    """List transactions for the current user."""
    user_id = user_payload["sub"]
    items, total = await service.list_transactions(
        user_id=user_id,
        page=page,
        page_size=page_size,
        transaction_type=transaction_type,
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ── Invoice Endpoints ──────────────────────────────────────────────────────


@router.post(
    "/invoices",
    response_model=InvoiceResponse,
    status_code=201,
    summary="Create invoice",
    description="Create a new invoice for a user.",
)
async def create_invoice(
    request: CreateInvoiceRequest,
    user_payload: dict = Depends(get_current_user_payload),
    service: BillingService = Depends(_get_billing_service),
):
    """Create a new invoice."""
    invoice = await service.create_invoice(request)
    return InvoiceResponse.model_validate(invoice)


@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get invoice",
    description="Get a specific invoice by ID.",
)
async def get_invoice(
    invoice_id: str,
    service: BillingService = Depends(_get_billing_service),
):
    """Get an invoice by ID."""
    invoice = await service.get_invoice(invoice_id)
    return InvoiceResponse.model_validate(invoice)


@router.get(
    "/invoices",
    response_model=InvoiceListResponse,
    summary="List invoices",
    description="List invoices with optional filters and pagination.",
)
async def list_invoices(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    user_id: str | None = Query(None, description="Filter by user ID"),
    user_payload: dict = Depends(get_current_user_payload),
    service: BillingService = Depends(_get_billing_service),
):
    """List invoices with optional filters."""
    items, total = await service.list_invoices(
        user_id=user_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(inv) for inv in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/invoices/{invoice_id}/mark-paid",
    response_model=InvoiceResponse,
    summary="Mark invoice as paid",
    description="Mark an existing invoice as paid.",
)
async def mark_invoice_paid(
    invoice_id: str,
    service: BillingService = Depends(_get_billing_service),
):
    """Mark an invoice as paid."""
    invoice = await service.mark_invoice_paid(invoice_id)
    return InvoiceResponse.model_validate(invoice)


@router.post(
    "/invoices/{invoice_id}/cancel",
    response_model=InvoiceResponse,
    summary="Cancel invoice",
    description="Cancel an existing invoice.",
)
async def cancel_invoice(
    invoice_id: str,
    service: BillingService = Depends(_get_billing_service),
):
    """Cancel an invoice."""
    invoice = await service.cancel_invoice(invoice_id)
    return InvoiceResponse.model_validate(invoice)


# ── Product Catalog Endpoints ──────────────────────────────────────────────


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=201,
    summary="Create product",
    description="Create a new product in the catalog.",
)
async def create_product(
    request: CreateProductRequest,
    service: BillingService = Depends(_get_billing_service),
):
    """Create a new product."""
    product = await service.create_product(request)
    return ProductResponse.model_validate(product)


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Get product",
    description="Get a specific product by ID.",
)
async def get_product(
    product_id: str,
    service: BillingService = Depends(_get_billing_service),
):
    """Get a product by ID."""
    product = await service.get_product(product_id)
    return ProductResponse.model_validate(product)


@router.get(
    "/products",
    response_model=ProductListResponse,
    summary="List products",
    description="List products with optional filters.",
)
async def list_products(
    module_name: str | None = Query(
        None, description="Filter by module name"
    ),
    active_only: bool = Query(True, description="Only active products"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    service: BillingService = Depends(_get_billing_service),
):
    """List products with optional filters."""
    items, total = await service.list_products(
        module_name=module_name,
        active_only=active_only,
        page=page,
        page_size=page_size,
    )
    return ProductListResponse(
        items=[ProductResponse.model_validate(p) for p in items],
        total=total,
    )


@router.put(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Update product",
    description="Update an existing product.",
)
async def update_product(
    product_id: str,
    request: UpdateProductRequest,
    service: BillingService = Depends(_get_billing_service),
):
    """Update a product."""
    product = await service.update_product(product_id, request)
    return ProductResponse.model_validate(product)


@router.delete(
    "/products/{product_id}",
    status_code=204,
    summary="Delete product",
    description="Soft-delete a product by setting it inactive.",
)
async def delete_product(
    product_id: str,
    service: BillingService = Depends(_get_billing_service),
) -> None:
    """Soft-delete a product."""
    await service.delete_product(product_id)


# ── Tenant Pricing Endpoints ────────────────────────────────────────────────


@router.put(
    "/tenants/{tenant_id}/pricing",
    response_model=TenantPricingResponse,
    summary="Set tenant pricing",
    description="Set or update tenant-specific product pricing.",
)
async def set_tenant_pricing(
    tenant_id: str,
    request: SetTenantPricingRequest,
    service: BillingService = Depends(_get_billing_service),
):
    """Set or update tenant-specific pricing."""
    pricing = await service.set_tenant_pricing(tenant_id, request)
    return TenantPricingResponse(
        id=str(pricing.id),
        tenant_id=str(pricing.tenant_id),
        product_id=str(pricing.product_id),
        price_override=pricing.price_override,
        created_at=pricing.created_at,
    )


@router.get(
    "/tenants/{tenant_id}/pricing",
    response_model=list[TenantPricingResponse],
    summary="List tenant pricing",
    description="List all custom pricing for a tenant.",
)
async def list_tenant_pricing(
    tenant_id: str,
    service: BillingService = Depends(_get_billing_service),
):
    """List all tenant-specific pricing."""
    pricing_list = await service.list_tenant_pricing(tenant_id)
    return [
        TenantPricingResponse(
            id=str(p.id),
            tenant_id=str(p.tenant_id),
            product_id=str(p.product_id),
            price_override=p.price_override,
            created_at=p.created_at,
        )
        for p in pricing_list
    ]


@router.delete(
    "/tenants/{tenant_id}/pricing/{product_id}",
    status_code=204,
    summary="Delete tenant pricing",
    description="Remove tenant-specific pricing for a product.",
)
async def delete_tenant_pricing(
    tenant_id: str,
    product_id: str,
    service: BillingService = Depends(_get_billing_service),
) -> None:
    """Remove tenant-specific pricing."""
    await service.delete_tenant_pricing(tenant_id, product_id)


# ── Commission Endpoints ───────────────────────────────────────────────────


@router.get(
    "/commissions",
    response_model=CommissionListResponse,
    summary="List commissions",
    description="List commissions with optional filters and pagination.",
)
async def list_commissions(
    reseller_id: str | None = Query(
        None, description="Filter by reseller ID"
    ),
    status: str | None = Query(
        None, description="Filter by status (pending, paid)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: BillingService = Depends(_get_billing_service),
):
    """List commissions with optional filters."""
    from shared.models.enums import CommissionStatus

    status_enum = None
    if status:
        status_enum = CommissionStatus(status)

    items, total = await service.list_commissions(
        reseller_id=reseller_id,
        status=status_enum,
        page=page,
        page_size=page_size,
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return CommissionListResponse(
        items=[CommissionResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/commissions/mark-paid",
    response_model=list[CommissionResponse],
    summary="Mark commissions paid",
    description="Mark one or more commissions as paid.",
)
async def mark_commissions_paid(
    request: MarkCommissionPaidRequest,
    service: BillingService = Depends(_get_billing_service),
):
    """Mark commissions as paid."""
    commissions = await service.mark_commissions_paid(request)
    return [CommissionResponse.model_validate(c) for c in commissions]


# ── Billing Summary & Reports ──────────────────────────────────────────────


@router.get(
    "/summary",
    response_model=BillingSummaryResponse,
    summary="Billing summary",
    description="Get a billing summary for the authenticated user.",
)
async def get_billing_summary(
    user_payload: dict = Depends(get_current_user_payload),
    service: BillingService = Depends(_get_billing_service),
):
    """Get billing summary for the current user."""
    user_id = user_payload["sub"]
    result = await service.get_billing_summary(user_id)
    return BillingSummaryResponse(**result)


@router.get(
    "/revenue-report",
    response_model=RevenueReportResponse,
    summary="Revenue report",
    description="Get a revenue report for a specific date range.",
)
async def get_revenue_report(
    period_start: datetime = Query(
        ..., description="Start of the reporting period"
    ),
    period_end: datetime = Query(
        ..., description="End of the reporting period"
    ),
    service: BillingService = Depends(_get_billing_service),
):
    """Get revenue report for a date range."""
    result = await service.get_revenue_report(period_start, period_end)
    return RevenueReportResponse(**result)


__all__ = ["router"]
