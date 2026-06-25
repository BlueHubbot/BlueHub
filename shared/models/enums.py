"""
BlueHub Shared Enums
=====================
Enumerations used across the database models.
"""

from enum import Enum


class UserRole(str, Enum):
    """User roles for RBAC."""

    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    RESELLER = "reseller"
    USER = "user"


class ServiceStatus(str, Enum):
    """Service lifecycle statuses."""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    TERMINATED = "terminated"


class ServiceModule(str, Enum):
    """Registered service module names."""

    VPN = "vpn"
    VPS = "vps"
    SMARTDNS = "smartdns"
    STREAMING = "streaming"
    GAME = "game"


class CommissionStatus(str, Enum):
    """Commission payout statuses."""

    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class AuditAction(str, Enum):
    """Common audit log action types."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    SUSPEND = "suspend"
    UNSUSPEND = "unsuspend"
    TERMINATE = "terminate"
    PAYMENT = "payment"
    REFUND = "refund"


class ModuleFlag(str, Enum):
    """Feature flags for module control."""

    STOP_NEW_SALES = "stop_new_sales"
    TERMINATE_SERVICES = "terminate_services"
    MAINTENANCE_MODE = "maintenance_mode"


class VpnProtocol(str, Enum):
    """Supported VPN protocols."""

    WIREGUARD = "wireguard"
    VLESS = "vless"
    TROJAN = "trojan"
    SHADOWSOCKS = "shadowsocks"


class VpnAccountStatus(str, Enum):
    """VPN account statuses."""

    ACTIVE = "active"
    DISABLED = "disabled"
    EXPIRED = "expired"


class VpnSessionStatus(str, Enum):
    """VPN session connection statuses."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    TIMEOUT = "timeout"


class VpsPowerStatus(str, Enum):
    """VPS instance power states."""

    RUNNING = "running"
    STOPPED = "stopped"
    SUSPENDED = "suspended"


class AbuseReportStatus(str, Enum):
    """Abuse report resolution statuses."""

    PENDING = "pending"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class VpnServerStatus(str, Enum):
    """VPN server statuses."""

    ACTIVE = "active"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


class BillingCycle(str, Enum):
    """Product billing cycle types."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUALLY = "semi_annually"
    ANNUALLY = "annually"
    BIENNIALLY = "biennially"
    TRIENNIALLY = "triennially"


__all__ = [
    "AuditAction",
    "BillingCycle",
    "CommissionStatus",
    "ModuleFlag",
    "ServiceModule",
    "ServiceStatus",
    "UserRole",
    "VpnAccountStatus",
    "VpnProtocol",
    "VpnServerStatus",
    "VpnSessionStatus",
    "VpsPowerStatus",
]
