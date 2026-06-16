"""
BlueHub Billing Schemas
=======================
Pydantic schemas for billing operations including wallet management,
invoices, transactions, product pricing, and commission tracking.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared.models.enums import BillingCycle, CommissionStatus

# ── Wallet Schemas ─────────────────────────────────────────────────────────


class WalletBalanceResponse(BaseModel):
    """Response schema for wallet balance queries."""

    user_id: str
    wallet_balance: float
    currency: str = "USD"

    model_config = ConfigDict(from_attributes=True)


class WalletTopUpRequest(BaseModel):
    """Request schema for wallet top-up."""

    amount: float = Field(..., gt=0, description="Amount to add to wallet")
    description: str | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """Ensure amount has at most 2 decimal places."""
        return round(v, 2)


class WalletDeductRequest(BaseModel):
    """Request schema for wallet deduction."""

    amount: float = Field(..., gt=0, description="Amount to deduct from wallet")
    description: str | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """Ensure amount has at most 2 decimal places."""
        return round(v, 2)


# ── Transaction Schemas ─────────────────────────────────────────────────────


class TransactionType(str):
    """Transaction type constants."""
    TOP_UP = "top_up"
    DEDUCTION = "deduction"
    PAYMENT = "payment"
    REFUND = "refund"
    COMMISSION = "commission"
    ADJUSTMENT = "adjustment"


class TransactionResponse(BaseModel):
    """Response schema for transaction records."""

    id: str
    user_id: str
    amount: float
    transaction_type: str
    description: str | None = None
    reference_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    """Paginated transaction list response."""

    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


# ── Invoice Schemas ─────────────────────────────────────────────────────────


class InvoiceStatus(str):
    """Invoice status constants."""
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class InvoiceResponse(BaseModel):
    """Response schema for invoice records."""

    id: str
    user_id: str
    service_id: str | None = None
    invoice_number: str
    amount: float
    status: str
    due_date: datetime
    paid_at: datetime | None = None
    description: str | None = None
    line_items: list[dict] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceListResponse(BaseModel):
    """Paginated invoice list response."""

    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


class CreateInvoiceRequest(BaseModel):
    """Request schema for creating a new invoice."""

    user_id: str
    service_id: str | None = None
    amount: float = Field(..., gt=0)
    due_date: datetime
    description: str | None = None
    line_items: list[dict] | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """Ensure amount has at most 2 decimal places."""
        return round(v, 2)


# ── Product Pricing Schemas ──────────────────────────────────────────────────


class ProductResponse(BaseModel):
    """Response schema for product catalog items."""

    id: str
    module_name: str
    product_key: str
    name: str
    description_i18n: dict | None = None
    base_price: float
    billing_cycle: BillingCycle
    billing_cycle_days: int
    specs: dict | None = None
    order: int
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    """Response schema for list of products."""

    items: list[ProductResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)


class CreateProductRequest(BaseModel):
    """Request schema for creating a new product."""

    module_name: str = Field(..., min_length=1, max_length=50)
    product_key: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    description_i18n: dict | None = None
    base_price: float = Field(..., gt=0)
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    billing_cycle_days: int = Field(..., gt=0)
    specs: dict | None = None
    order: int = 0
    active: bool = True

    @field_validator("base_price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Ensure price has at most 2 decimal places."""
        return round(v, 2)


class UpdateProductRequest(BaseModel):
    """Request schema for updating an existing product."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description_i18n: dict | None = None
    base_price: float | None = Field(None, gt=0)
    billing_cycle: BillingCycle | None = None
    billing_cycle_days: int | None = Field(None, gt=0)
    specs: dict | None = None
    order: int | None = None
    active: bool | None = None

    @field_validator("base_price")
    @classmethod
    def validate_price(cls, v: float | None) -> float | None:
        """Ensure price has at most 2 decimal places."""
        if v is not None:
            return round(v, 2)
        return v


# ── Tenant Pricing Schemas ───────────────────────────────────────────────────


class TenantPricingResponse(BaseModel):
    """Response schema for tenant-specific pricing."""

    id: str
    tenant_id: str
    product_id: str
    product_name: str | None = None
    price_override: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SetTenantPricingRequest(BaseModel):
    """Request schema for setting tenant-specific pricing."""

    product_id: str
    price_override: float = Field(..., gt=0)

    @field_validator("price_override")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Ensure price has at most 2 decimal places."""
        return round(v, 2)


# ── Commission Schemas ───────────────────────────────────────────────────────


class CommissionResponse(BaseModel):
    """Response schema for commission records."""

    id: str
    reseller_id: str
    service_id: str
    commission_rate: float
    commission_amount: float
    status: CommissionStatus
    paid_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommissionListResponse(BaseModel):
    """Paginated commission list response."""

    items: list[CommissionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


class MarkCommissionPaidRequest(BaseModel):
    """Request schema for marking commissions as paid."""

    commission_ids: list[str] = Field(..., min_length=1)


# ── Billing Summary Schemas ──────────────────────────────────────────────────


class BillingSummaryResponse(BaseModel):
    """Summary of user's billing information."""

    wallet_balance: float
    total_invoices: int
    paid_invoices: int
    pending_invoices: int
    overdue_invoices: int
    total_spent: float
    pending_commissions: float | None = None
    total_commissions: float | None = None

    model_config = ConfigDict(from_attributes=True)


class RevenueReportResponse(BaseModel):
    """Revenue report for a date range."""

    total_revenue: float
    total_commissions: float
    net_revenue: float
    invoice_count: int
    top_up_count: int
    period_start: datetime
    period_end: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "BillingSummaryResponse",
    "CommissionListResponse",
    "CommissionResponse",
    "CreateInvoiceRequest",
    "CreateProductRequest",
    "InvoiceListResponse",
    "InvoiceResponse",
    "InvoiceStatus",
    "MarkCommissionPaidRequest",
    "ProductListResponse",
    "ProductResponse",
    "RevenueReportResponse",
    "SetTenantPricingRequest",
    "TenantPricingResponse",
    "TransactionListResponse",
    "TransactionResponse",
    "TransactionType",
    "UpdateProductRequest",
    "WalletBalanceResponse",
    "WalletDeductRequest",
    "WalletTopUpRequest",
]
