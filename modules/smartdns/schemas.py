"""
BlueHub SmartDNS Schemas
=========================
Pydantic request/response schemas for SmartDNS profile and DNS record management.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------
# Profile schemas
# ------------------------------------------------------------------
class SmartDnsProfileBase(BaseModel):
    """Common fields shared across SmartDNS profile schemas."""

    profile_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["My Netflix Profile"],
        description="User-visible name for this DNS profile",
    )
    upstream_dns: str = Field(
        default="8.8.8.8",
        max_length=255,
        description="Upstream DNS resolver for unhandled queries",
    )
    geo_region: str | None = Field(
        default=None,
        max_length=50,
        description="Target geo region for unblock (e.g., US, UK, DE, JP)",
    )
    allowed_ips: list[str] | None = Field(
        default=None,
        description="List of IP addresses/CIDRs allowed to query this profile",
    )
    max_queries_per_second: int | None = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum DNS queries per second allowed",
    )
    enable_dnssec: bool = Field(
        default=False,
        description="Enable DNSSEC validation for this profile",
    )
    enable_logging: bool = Field(
        default=True,
        description="Enable query logging for this profile",
    )
    enable_ad_blocking: bool = Field(
        default=False,
        description="Enable ad/malware domain blocking",
    )
    extra_config: dict | None = Field(
        default=None,
        description="Additional configuration as key-value dict",
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Admin notes",
    )


class SmartDnsProfileCreate(SmartDnsProfileBase):
    """Schema for creating a new SmartDNS profile."""

    service_id: UUID = Field(..., description="Associated billing service ID")


class SmartDnsProfileUpdate(BaseModel):
    """Schema for updating an existing SmartDNS profile."""

    profile_name: str | None = Field(default=None, max_length=100)
    upstream_dns: str | None = Field(default=None, max_length=255)
    geo_region: str | None = Field(default=None, max_length=50)
    allowed_ips: list[str] | None = None
    max_queries_per_second: int | None = Field(default=None, ge=1, le=10000)
    enable_dnssec: bool | None = None
    enable_logging: bool | None = None
    enable_ad_blocking: bool | None = None
    extra_config: dict | None = None
    notes: str | None = Field(default=None, max_length=2000)


class SmartDnsProfileResponse(SmartDnsProfileBase):
    """Full SmartDNS profile response returned to API consumers."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_id: UUID
    status: str = Field(description="Profile status: active, disabled, error, provisioning")
    pdns_zone_id: str | None = None
    pdns_zone_name: str | None = None
    total_queries: int = 0
    created_at: datetime
    updated_at: datetime


class SmartDnsProfileSummary(BaseModel):
    """Lightweight SmartDNS profile representation for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_id: UUID
    profile_name: str
    status: str
    geo_region: str | None
    pdns_zone_name: str | None
    total_queries: int
    created_at: datetime


class SmartDnsStatusResponse(BaseModel):
    """Live status information for a SmartDNS profile."""

    profile_id: UUID
    status: str
    zone_name: str | None
    zone_id: str | None
    record_count: int
    total_queries: int
    max_qps: int | None
    dnssec_enabled: bool
    ad_blocking_enabled: bool


# ------------------------------------------------------------------
# DNS Record schemas
# ------------------------------------------------------------------
class DnsRecordCreate(BaseModel):
    """Schema for adding a DNS record to a profile."""

    record_type: str = Field(
        ...,
        pattern=r"^(A|AAAA|CNAME|MX|TXT|NS|SRV|PTR)$",
        description="DNS record type",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="DNS record name (e.g., www, @ for root)",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="DNS record content/value",
    )
    ttl: int = Field(
        default=300,
        ge=1,
        le=86400,
        description="Time-to-live in seconds",
    )
    priority: int | None = Field(
        default=0,
        ge=0,
        le=65535,
        description="Priority for MX/SRV records",
    )


class DnsRecordUpdate(BaseModel):
    """Schema for updating a DNS record."""

    name: str | None = Field(default=None, max_length=255)
    content: str | None = Field(default=None, max_length=500)
    ttl: int | None = Field(default=None, ge=1, le=86400)
    priority: int | None = Field(default=None, ge=0, le=65535)
    disabled: bool | None = None


class DnsRecordResponse(BaseModel):
    """DNS record returned to API consumers."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_id: UUID
    record_type: str
    name: str
    content: str
    ttl: int
    priority: int | None
    disabled: bool
    synced: bool
    synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DnsRecordBulkCreate(BaseModel):
    """Bulk creation of multiple DNS records at once."""

    records: list[DnsRecordCreate] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of DNS records to create",
    )


class DnsRecordBulkResponse(BaseModel):
    """Response for bulk DNS record operations."""

    profile_id: UUID
    created: int = 0
    failed: int = 0
    records: list[DnsRecordResponse] = []
    errors: list[str] = []


# ------------------------------------------------------------------
# Import / sync
# ------------------------------------------------------------------
class SmartDnsImportRequest(BaseModel):
    """Request to import DNS records from an external zone file or URL."""

    source_type: str = Field(
        ...,
        pattern=r"^(zone_file|bind_zone|url|json)$",
        description="Source format: zone_file, bind_zone, url, json",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Zone file content, URL, or JSON payload",
    )


class SmartDnsSyncResponse(BaseModel):
    """Response after syncing DNS records with PowerDNS."""

    profile_id: UUID
    synced: int = 0
    failed: int = 0
    errors: list[str] = []


__all__ = [
    # Profile
    "SmartDnsProfileCreate",
    "SmartDnsProfileUpdate",
    "SmartDnsProfileResponse",
    "SmartDnsProfileSummary",
    "SmartDnsStatusResponse",
    # DNS Records
    "DnsRecordCreate",
    "DnsRecordUpdate",
    "DnsRecordResponse",
    "DnsRecordBulkCreate",
    "DnsRecordBulkResponse",
    # Import / Sync
    "SmartDnsImportRequest",
    "SmartDnsSyncResponse",
]
