"""
VPN Module Database Models
===========================
SQLAlchemy ORM models for VPN services:
- VpnAccount: stores VPN account credentials and protocol config for each service
- VpnSession: logs connection/disconnection events
- VpnProtocolConfig: stores protocol-specific configuration parameters
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import CoreBase, TimestampMixin, UUIDMixin
from shared.models.enums import VpnAccountStatus, VpnProtocol, VpnSessionStatus

if TYPE_CHECKING:
    from shared.models.service import Service


class VpnServer(UUIDMixin, TimestampMixin, CoreBase):
    """
    VPN server instance that hosts VPN accounts.
    Stores connection details, capacity, and WireGuard key material.
    """

    __tablename__ = "vpn_servers"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Human-readable server name",
    )
    host: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Server hostname or IP address for management SSH/API",
    )
    port: Mapped[int] = mapped_column(
        default=51820,
        nullable=False,
        doc="WireGuard listen port",
    )
    public_ip: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
        doc="Server public IP address for client configuration",
    )
    private_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Server WireGuard private key (stored encrypted)",
    )
    public_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Server WireGuard public key",
    )
    endpoint: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Server endpoint for client config (IP:Port or domain:Port)",
    )
    country: Mapped[str] = mapped_column(
        String(2),
        default="US",
        nullable=False,
        doc="ISO 3166-1 alpha-2 country code",
    )
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Server city location",
    )
    provider: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Server hosting provider name",
    )
    bandwidth_limit_mbps: Mapped[int | None] = mapped_column(
        nullable=True,
        doc="Bandwidth limit in Mbps for this server",
    )
    max_clients: Mapped[int] = mapped_column(
        default=100,
        nullable=False,
        doc="Maximum number of client peers this server can host",
    )
    current_clients: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        doc="Current number of active client peers",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        doc="Whether this server is accepting new clients",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Admin notes",
    )

    # Relationships
    vpn_accounts: Mapped[list[VpnAccount]] = relationship(
        "VpnAccount",
        back_populates="server_rel",
        lazy="selectin",
        foreign_keys="VpnAccount.server_id",
    )

    def __repr__(self) -> str:
        return (
            f"<VpnServer(id={self.id}, name={self.name!r}, "
            f"host={self.host!r}, country={self.country!r})>"
        )


class VpnAccount(UUIDMixin, TimestampMixin, CoreBase):
    """
    VPN account linked one-to-one with a Service record.
    Stores protocol type, credentials, and usage limits.
    """

    __tablename__ = "vpn_accounts"

    service_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        doc="Foreign key to services table (one-to-one)",
    )
    protocol: Mapped[VpnProtocol] = mapped_column(
        default=VpnProtocol.WIREGUARD,
        nullable=False,
        index=True,
        doc="VPN protocol (wireguard, vless, trojan, shadowsocks)",
    )
    status: Mapped[VpnAccountStatus] = mapped_column(
        default=VpnAccountStatus.ACTIVE,
        nullable=False,
        index=True,
        doc="Account status",
    )
    # WireGuard-specific fields
    private_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="WireGuard private key (server-side stored encrypted)",
    )
    public_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="WireGuard public key",
    )
    preshared_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="WireGuard preshared key for additional encryption",
    )
    # VLESS / Trojan / Shadowsocks UUID / password
    password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Protocol password, UUID (VLESS), or trojan password",
    )
    # IP assignment
    assigned_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        doc="Assigned VPN IP address (IPv4 or IPv6)",
    )
    dns_servers: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Comma-separated DNS server addresses",
    )
    allowed_ips: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Comma-separated allowed IP ranges (e.g. 0.0.0.0/0)",
    )
    # Traffic and usage limits
    bandwidth_limit_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        doc="Total bandwidth limit in bytes (null = unlimited)",
    )
    bandwidth_used_bytes: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        doc="Total bandwidth used in bytes",
    )
    max_connections: Mapped[int] = mapped_column(
        default=3,
        nullable=False,
        doc="Maximum concurrent connections allowed",
    )
    # Provisioning metadata
    server_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vpn_servers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Assigned VPN server",
    )
    provisioned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the account was provisioned on the server",
    )
    last_handshake_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last successful handshake timestamp",
    )
    # Config file (generated client config)
    client_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Generated client configuration text (e.g. wg-quick config)",
    )
    # Extra metadata
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Admin notes for this account",
    )

    # Relationships
    service: Mapped[Service] = relationship(
        "Service",
        back_populates="vpn_account",
        lazy="selectin",
        uselist=False,
    )
    sessions: Mapped[list[VpnSession]] = relationship(
        "VpnSession",
        back_populates="vpn_account",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    protocol_configs: Mapped[list[VpnProtocolConfig]] = relationship(
        "VpnProtocolConfig",
        back_populates="vpn_account",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    server_rel: Mapped[VpnServer | None] = relationship(
        "VpnServer",
        back_populates="vpn_accounts",
        lazy="selectin",
        uselist=False,
        foreign_keys=[server_id],
    )

    def __repr__(self) -> str:
        return (
            f"<VpnAccount(id={self.id}, service_id={self.service_id}, "
            f"protocol={self.protocol.value}, status={self.status.value})>"
        )


class VpnProtocolConfig(UUIDMixin, TimestampMixin, CoreBase):
    """
    Protocol-specific configuration parameters stored as key-value pairs.
    Allows flexible per-protocol settings without schema changes.
    """

    __tablename__ = "vpn_protocol_configs"

    vpn_account_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vpn_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to vpn_accounts table",
    )
    config_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Configuration key (e.g. sni, flow, network, security, fingerprint)",
    )
    config_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Configuration value as text (JSON-encoded for complex values)",
    )

    # Relationships
    vpn_account: Mapped[VpnAccount] = relationship(
        "VpnAccount",
        back_populates="protocol_configs",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<VpnProtocolConfig(id={self.id}, account_id={self.vpn_account_id}, "
            f"key={self.config_key!r})>"
        )


class VpnSession(UUIDMixin, TimestampMixin, CoreBase):
    """
    VPN session log recording connection and disconnection events.
    Used for traffic analytics, concurrent connection tracking, and billing.
    """

    __tablename__ = "vpn_sessions"

    vpn_account_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vpn_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to vpn_accounts table",
    )
    status: Mapped[VpnSessionStatus] = mapped_column(
        default=VpnSessionStatus.CONNECTED,
        nullable=False,
        index=True,
        doc="Session status",
    )
    # Connection details
    connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Connection start timestamp",
    )
    disconnected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Connection end timestamp",
    )
    # Client info
    client_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        doc="Client public IP address at connection time",
    )
    client_port: Mapped[int | None] = mapped_column(
        nullable=True,
        doc="Client port number",
    )
    # Traffic counters (updated on disconnect / periodic polling)
    bytes_sent: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        doc="Bytes sent to client during this session",
    )
    bytes_received: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        doc="Bytes received from client during this session",
    )
    # Endpoint info
    server_endpoint: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Server endpoint used for this connection",
    )
    # Disconnect reason
    disconnect_reason: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Reason for disconnection (timeout, manual, error, etc.)",
    )

    # Relationships
    vpn_account: Mapped[VpnAccount] = relationship(
        "VpnAccount",
        back_populates="sessions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<VpnSession(id={self.id}, account_id={self.vpn_account_id}, "
            f"status={self.status.value})>"
        )


__all__ = [
    "VpnAccount",
    "VpnProtocolConfig",
    "VpnSession",
    "VpnServer",
]
