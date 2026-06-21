"""
BlueHub Shared Models
======================
SQLAlchemy ORM models for the BlueHub platform.
"""

from shared.models.abuse_report import AbuseReport
from shared.models.audit_log import AuditLog
from shared.models.base import CoreBase, IDMixin, SoftDeleteMixin, TimestampMixin, UUIDMixin
from shared.models.enums import (
    AuditAction,
    BillingCycle,
    CommissionStatus,
    ModuleFlag,
    ServiceModule,
    ServiceStatus,
    UserRole,
    VpnAccountStatus,
    VpnProtocol,
    VpnSessionStatus,
    VpsPowerStatus,
)
from shared.models.invoice import Invoice
from shared.models.module_registry import ModuleRegistry
from shared.models.paymenter_webhook import PaymenterWebhookEvent
from shared.models.product import Product, ResellerCommission, TenantProductPricing
from shared.models.service import Service
from shared.models.tenant import Tenant
from shared.models.transaction import Transaction
from shared.models.user import User

# NOTE: VPN/VPS module models must be imported directly from modules.vpn.models / modules.vps.models
# shared.models (core) MUST NOT import from modules/ per AGENTS.md architectural invariant.
__all__ = [
    "AbuseReport",
    "AuditAction",
    "AuditLog",
    "BillingCycle",
    "CommissionStatus",
    "CoreBase",
    "IDMixin",
    "Invoice",
    "ModuleFlag",
    "ModuleRegistry",
    "PaymenterWebhookEvent",
    "Product",
    "ResellerCommission",
    "Service",
    "ServiceModule",
    "ServiceStatus",
    "SoftDeleteMixin",
    "Tenant",
    "TenantProductPricing",
    "TimestampMixin",
    "Transaction",
    "UUIDMixin",
    "User",
    "UserRole",
    "VpnAccountStatus",
    "VpnProtocol",
    "VpnSessionStatus",
    "VpsPowerStatus",
]
