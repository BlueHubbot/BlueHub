"""
BlueHub Shared Models
======================
SQLAlchemy ORM models for the BlueHub platform.
"""

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

# Import VPN module models
from modules.vpn.models import VpnAccount, VpnProtocolConfig, VpnSession

# Import VPS module models
from modules.vps.models import VpsInstance, VpsSnapshot

__all__ = [
    "AuditAction",
    "AuditLog",
    "BillingCycle",
    "CommissionStatus",
    # Base
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
    # Core Models
    "Tenant",
    "TenantProductPricing",
    "TimestampMixin",
    "Transaction",
    "UUIDMixin",
    "User",
    # Enums
    "UserRole",
    "VpnAccount",
    "VpnAccountStatus",
    "VpnProtocol",
    "VpnProtocolConfig",
    "VpnSession",
    "VpnSessionStatus",
    "VpsInstance",
    "VpsPowerStatus",
    "VpsSnapshot",
]
