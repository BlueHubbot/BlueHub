"""
VPN Module Pydantic Schemas
=============================
Request/response schemas for VPN module API endpoints.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# VPN Server Schemas
# ---------------------------------------------------------------------------


class VpnServerCreate(BaseModel):
    """Schema for creating a new VPN server."""

    name: str = Field(..., min_length=1, max_length=100, description="Server name")
    host: str = Field(..., min_length=1, max_length=255, description="Server hostname or IP")
    port: int = Field(51820, ge=1, le=65535, description="Server port")
    public_ip: str = Field(..., min_length=7, max_length=45, description="Server public IP address")
    private_key: str | None = Field(None, description="Server WireGuard private key")
    public_key: str | None = Field(None, description="Server WireGuard public key")
    endpoint: str = Field(..., min_length=1, max_length=255, description="Server endpoint URL/IP:Port")
    country: str = Field(default="US", max_length=2, description="ISO 3166-1 alpha-2 country code")
    city: str | None = Field(None, max_length=100, description="Server city location")
    provider: str | None = Field(None, max_length=100, description="Server provider name")
    bandwidth_limit_mbps: int | None = Field(None, ge=0, description="Bandwidth limit in Mbps")
    max_clients: int = Field(100, ge=1, description="Maximum number of clients")
    is_active: bool = Field(True, description="Whether the server is active")


class VpnServerUpdate(BaseModel):
    """Schema for updating a VPN server."""

    name: str | None = Field(None, min_length=1, max_length=100)
    host: str | None = Field(None, min_length=1, max_length=255)
    port: int | None = Field(None, ge=1, le=65535)
    public_ip: str | None = Field(None, min_length=7, max_length=45)
    private_key: str | None = None
    public_key: str | None = None
    endpoint: str | None = Field(None, min_length=1, max_length=255)
    country: str | None = Field(None, max_length=2)
    city: str | None = Field(None, max_length=100)
    provider: str | None = Field(None, max_length=100)
    bandwidth_limit_mbps: int | None = Field(None, ge=0)
    max_clients: int | None = Field(None, ge=1)
    is_active: bool | None = None


class VpnServerResponse(BaseModel):
    """Schema for VPN server response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    host: str
    port: int
    public_ip: str
    endpoint: str
    country: str
    city: str | None
    provider: str | None
    bandwidth_limit_mbps: int | None
    max_clients: int
    current_clients: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# VPN Account Schemas
# ---------------------------------------------------------------------------


class VpnAccountCreate(BaseModel):
    """Schema for creating a new VPN account (provisioning)."""

    service_id: str = Field(..., description="UUID of the associated service")
    protocol: str = Field("wireguard", description="VPN protocol (wireguard, vless, trojan, shadowsocks)")
    assigned_ip: str | None = Field(None, max_length=45, description="Assigned VPN IP")
    dns_servers: str | None = Field(None, max_length=255, description="Comma-separated DNS servers")
    allowed_ips: str | None = Field(None, description="Comma-separated allowed IP ranges")
    bandwidth_limit_bytes: int | None = Field(None, ge=0, description="Bandwidth limit in bytes")
    max_connections: int = Field(3, ge=1, le=100, description="Max concurrent connections")
    server_id: str | None = Field(None, description="UUID of the assigned VPN server")
    notes: str | None = Field(None, description="Admin notes")


class VpnAccountUpdate(BaseModel):
    """Schema for updating a VPN account."""

    protocol: str | None = None
    status: str | None = None
    password: str | None = None
    assigned_ip: str | None = Field(None, max_length=45)
    dns_servers: str | None = Field(None, max_length=255)
    allowed_ips: str | None = None
    bandwidth_limit_bytes: int | None = Field(None, ge=0)
    max_connections: int | None = Field(None, ge=1, le=100)
    server_id: str | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("active", "disabled", "expired"):
            raise ValueError(f"Invalid status: {v}")
        return v

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, v: str | None) -> str | None:
        if v is not None and v not in ("wireguard", "vless", "trojan", "shadowsocks"):
            raise ValueError(f"Invalid protocol: {v}")
        return v


class VpnProtocolConfigSchema(BaseModel):
    """Schema for protocol-specific configuration."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    vpn_account_id: str
    config_key: str
    config_value: str
    created_at: datetime
    updated_at: datetime


class VpnProtocolConfigCreate(BaseModel):
    """Schema for creating a protocol configuration entry."""

    config_key: str = Field(..., min_length=1, max_length=100, description="Configuration key")
    config_value: str = Field(..., min_length=1, description="Configuration value")


class VpnAccountResponse(BaseModel):
    """Schema for VPN account response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    service_id: str
    protocol: str
    status: str
    public_key: str | None
    password: str | None
    assigned_ip: str | None
    dns_servers: str | None
    allowed_ips: str | None
    bandwidth_limit_bytes: int | None
    bandwidth_used_bytes: int
    max_connections: int
    server_id: str | None
    provisioned_at: datetime | None
    last_handshake_at: datetime | None
    client_config: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    # Nested relationships
    protocol_configs: list[VpnProtocolConfigSchema] = Field(default_factory=list)
    sessions: list[VpnSessionSchema] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# VPN Session Schemas
# ---------------------------------------------------------------------------


class VpnSessionSchema(BaseModel):
    """Schema for VPN session response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    vpn_account_id: str
    status: str
    connected_at: datetime | None
    disconnected_at: datetime | None
    client_ip: str | None
    client_port: int | None
    bytes_sent: int
    bytes_received: int
    server_endpoint: str | None
    disconnect_reason: str | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# VPN Usage / Traffic Schemas
# ---------------------------------------------------------------------------


class VpnUsageSummary(BaseModel):
    """Schema for VPN usage summary (aggregated)."""

    model_config = ConfigDict(from_attributes=True)

    total_bytes_sent: int
    total_bytes_received: int
    total_bytes: int
    bandwidth_limit_bytes: int | None
    bandwidth_remaining_bytes: int | None
    bandwidth_used_percent: float | None
    current_sessions: int
    last_handshake_at: datetime | None


class VpnTrafficResponse(BaseModel):
    """Schema for VPN traffic data response."""

    account_id: str
    protocol: str
    status: str
    usage: VpnUsageSummary


# ---------------------------------------------------------------------------
# VPN Config Response
# ---------------------------------------------------------------------------


class VpnConfigResponse(BaseModel):
    """Schema for VPN client configuration download."""

    model_config = ConfigDict(from_attributes=True)

    account_id: str
    protocol: str
    config_text: str | None
    config_qr_base64: str | None = Field(None, description="QR code as base64-encoded PNG")


# ---------------------------------------------------------------------------
# VPN Purchase / Provision Schemas
# ---------------------------------------------------------------------------


class VpnPurchaseRequest(BaseModel):
    """Schema for initiating a VPN purchase."""

    product_id: str = Field(..., description="UUID of the VPN product")
    protocol: str = Field("wireguard", description="Desired VPN protocol")
    server_id: str | None = Field(None, description="Preferred server (optional)")
    billing_cycle: str = Field("monthly", description="Billing cycle (monthly, quarterly, annually)")


class VpnPurchaseResponse(BaseModel):
    """Schema for VPN purchase initiation response."""

    payment_url: str | None = Field(None, description="Redirect URL for payment")
    invoice_id: str | None = Field(None, description="UUID of the created invoice")
    service_id: str | None = Field(None, description="UUID of the created service (pending)")
    message: str = Field(..., description="Status message")


# ---------------------------------------------------------------------------
# VPN List Response
# ---------------------------------------------------------------------------


class VpnServiceListItem(BaseModel):
    """Schema for a single item in the VPN services list."""

    model_config = ConfigDict(from_attributes=True)

    service_id: str
    account_id: str | None
    protocol: str | None
    status: str
    assigned_ip: str | None
    bandwidth_used_bytes: int
    bandwidth_limit_bytes: int | None
    expires_at: datetime | None
    provisioned_at: datetime | None
    last_handshake_at: datetime | None


class VpnServiceListResponse(BaseModel):
    """Schema for the list of user's VPN services."""

    services: list[VpnServiceListItem]
    total: int


# ---------------------------------------------------------------------------
# VPN Product Schemas
# ---------------------------------------------------------------------------


class VpnProductResponse(BaseModel):
    """Schema for VPN product listing."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    protocols: list[str] = Field(default_factory=list, description="Available protocols")
    bandwidth: str | None = Field(None, description="Bandwidth limit description")
    speed: str | None = Field(None, description="Speed limit description")
    price_monthly: float | None
    price_quarterly: float | None
    price_semi_annually: float | None
    price_annually: float | None
    is_active: bool


__all__ = [
    "VpnAccountCreate",
    "VpnAccountResponse",
    "VpnAccountUpdate",
    "VpnConfigResponse",
    "VpnProductResponse",
    "VpnProtocolConfigCreate",
    "VpnProtocolConfigSchema",
    "VpnPurchaseRequest",
    "VpnPurchaseResponse",
    "VpnServerCreate",
    "VpnServerResponse",
    "VpnServerUpdate",
    "VpnServiceListItem",
    "VpnServiceListResponse",
    "VpnSessionSchema",
    "VpnTrafficResponse",
    "VpnUsageSummary",
]
