"""
BlueHub Billing Module
======================
Payment processing, invoice management, subscription lifecycle.
Integrates with Paymenter for billing operations.
"""

from __future__ import annotations

from core.billing.schemas import (
    BillingSummaryResponse,
    CommissionListResponse,
    CommissionResponse,
    CreateInvoiceRequest,
    CreateProductRequest,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceStatus,
    MarkCommissionPaidRequest,
    ProductListResponse,
    ProductResponse,
    RevenueReportResponse,
    SetTenantPricingRequest,
    TenantPricingResponse,
    TransactionListResponse,
    TransactionResponse,
    TransactionType,
    UpdateProductRequest,
    WalletBalanceResponse,
    WalletDeductRequest,
    WalletTopUpRequest,
)
from core.billing.service import (
    BillingError,
    BillingService,
    CommissionNotFoundError,
    DuplicateInvoiceNumberError,
    InsufficientBalanceError,
    InvoiceNotFoundError,
    PricingNotFoundError,
    ProductNotFoundError,
    TransactionNotFoundError,
    UserNotFoundError,
)

__all__ = [
    # Exceptions
    "BillingError",
    # Service
    "BillingService",
    "BillingSummaryResponse",
    "CommissionListResponse",
    "CommissionNotFoundError",
    "CommissionResponse",
    "CreateInvoiceRequest",
    "CreateProductRequest",
    "DuplicateInvoiceNumberError",
    "InsufficientBalanceError",
    "InvoiceListResponse",
    "InvoiceNotFoundError",
    "InvoiceResponse",
    "InvoiceStatus",
    "MarkCommissionPaidRequest",
    "PricingNotFoundError",
    "ProductListResponse",
    "ProductNotFoundError",
    "ProductResponse",
    "RevenueReportResponse",
    "SetTenantPricingRequest",
    "TenantPricingResponse",
    "TransactionListResponse",
    "TransactionNotFoundError",
    "TransactionResponse",
    "TransactionType",
    "UpdateProductRequest",
    "UserNotFoundError",
    # Schemas
    "WalletBalanceResponse",
    "WalletDeductRequest",
    "WalletTopUpRequest",
]
