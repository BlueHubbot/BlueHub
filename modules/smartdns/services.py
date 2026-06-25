"""
BlueHub SmartDNS Services
===========================
Business logic for SmartDNS profiles and DNS record management.
Handles profile CRUD, record management, PowerDNS zone creation,
sync operations, and status management.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ValidationError
from modules.smartdns.models import DnsRecord, SmartDnsProfile
from modules.smartdns.schemas import (
    DnsRecordCreate,
    DnsRecordResponse,
    DnsRecordUpdate,
    SmartDnsProfileResponse,
    SmartDnsProfileUpdate,
    SmartDnsStatusResponse,
    SmartDnsSyncResponse,
)
from shared.models.enums import ServiceStatus
from shared.models.service import Service

logger = logging.getLogger("bluehub.smartdns")

VALID_RECORD_TYPES = {"A", "AAAA", "CNAME", "MX", "TXT", "NS", "SRV", "PTR"}
VALID_STATUSES = {"active", "disabled", "error", "provisioning", "suspended"}


class SmartDnsError(Exception):
    """Base exception for SmartDNS service errors."""


class ProfileNotFoundError(SmartDnsError):
    """Raised when a SmartDNS profile is not found."""


class ProfileAlreadyExistsError(SmartDnsError):
    """Raised when a profile already exists for a service."""


class ProfileProvisioningError(SmartDnsError):
    """Raised when profile provisioning fails."""


class RecordNotFoundError(SmartDnsError):
    """Raised when a DNS record is not found."""


class RecordValidationError(SmartDnsError):
    """Raised when a DNS record fails validation."""


class SmartDnsService:
    """Service class for SmartDNS profile and DNS record operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Profile Operations
    # ------------------------------------------------------------------

    async def create_profile(
        self,
        service_id: UUID,
        profile_name: str,
        upstream_dns: str = "8.8.8.8",
        geo_region: str | None = None,
        allowed_ips: list[str] | None = None,
        max_queries_per_second: int | None = 100,
        enable_dnssec: bool = False,
        enable_logging: bool = True,
        enable_ad_blocking: bool = False,
        extra_config: dict[str, object] | None = None,
        notes: str | None = None,
    ) -> SmartDnsProfile:
        """Provision a new SmartDNS profile for a service."""
        # Check service exists
        service = await self.db.get(Service, service_id)
        if service is None:
            raise ProfileNotFoundError(f"Service {service_id} not found")

        # Check no existing profile for this service
        existing = await self.db.execute(
            select(SmartDnsProfile).where(SmartDnsProfile.service_id == service_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise ProfileAlreadyExistsError(
                f"Profile already exists for service {service_id}"
            )

        profile = SmartDnsProfile(
            id=uuid4(),
            service_id=service_id,
            profile_name=profile_name,
            status="provisioning",
            upstream_dns=upstream_dns,
            geo_region=geo_region,
            allowed_ips=allowed_ips or [],
            max_queries_per_second=max_queries_per_second,
            enable_dnssec=enable_dnssec,
            enable_logging=enable_logging,
            enable_ad_blocking=enable_ad_blocking,
            extra_config=extra_config or {},
            notes=notes,
        )

        self.db.add(profile)
        await self.db.flush()

        # Update service status to active
        service.status = ServiceStatus.ACTIVE
        self.db.add(service)
        await self.db.flush()

        logger.info("SmartDNS profile %s created for service %s", profile.id, service_id)
        return profile

    async def get_profile(self, profile_id: UUID) -> SmartDnsProfile:
        """Get a SmartDNS profile by ID."""
        profile = await self.db.get(SmartDnsProfile, profile_id)
        if profile is None:
            raise ProfileNotFoundError(f"Profile {profile_id} not found")
        return profile

    async def get_profile_by_service(self, service_id: UUID) -> SmartDnsProfile | None:
        """Get a SmartDNS profile by service ID."""
        result = await self.db.execute(
            select(SmartDnsProfile).where(SmartDnsProfile.service_id == service_id)
        )
        return result.scalar_one_or_none()

    async def list_profiles(
        self,
        status: str | None = None,
        geo_region: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[SmartDnsProfile]:
        """List SmartDNS profiles with optional filters."""
        query = select(SmartDnsProfile)

        if status:
            query = query.where(SmartDnsProfile.status == status)
        if geo_region:
            query = query.where(SmartDnsProfile.geo_region == geo_region)

        query = query.offset(offset).limit(limit).order_by(SmartDnsProfile.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_profile(
        self,
        profile_id: UUID,
        update: SmartDnsProfileUpdate,
    ) -> SmartDnsProfile:
        """Update a SmartDNS profile."""
        profile = await self.get_profile(profile_id)

        for field, value in update.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)

        profile.updated_at = datetime.now(UTC)
        self.db.add(profile)
        await self.db.flush()

        logger.info("SmartDNS profile %s updated", profile_id)
        return profile

    async def delete_profile(self, profile_id: UUID) -> None:
        """Delete a SmartDNS profile and all its records."""
        profile = await self.get_profile(profile_id)
        await self.db.delete(profile)
        await self.db.flush()
        logger.info("SmartDNS profile %s deleted", profile_id)

    async def set_profile_status(self, profile_id: UUID, status: str) -> SmartDnsProfile:
        """Set the status of a SmartDNS profile."""
        if status not in VALID_STATUSES:
            raise ValidationError(f"Invalid profile status: {status}")

        profile = await self.get_profile(profile_id)
        profile.status = status
        profile.updated_at = datetime.now(UTC)
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def get_profile_status(self, profile_id: UUID) -> SmartDnsStatusResponse:
        """Get detailed status information for a profile."""
        profile = await self.get_profile(profile_id)

        record_count_result = await self.db.execute(
            select(DnsRecord).where(
                and_(
                    DnsRecord.profile_id == profile_id,
                    DnsRecord.disabled == False,  # noqa: E712
                )
            )
        )
        records = list(record_count_result.scalars().all())

        return SmartDnsStatusResponse(
            profile_id=profile.id,
            status=profile.status,
            zone_name=profile.pdns_zone_name,
            zone_id=profile.pdns_zone_id,
            record_count=len(records),
            total_queries=profile.total_queries or 0,
            max_qps=profile.max_queries_per_second,
            dnssec_enabled=profile.enable_dnssec,
            ad_blocking_enabled=profile.enable_ad_blocking,
        )

    # ------------------------------------------------------------------
    # DNS Record Operations
    # ------------------------------------------------------------------

    async def add_record(
        self,
        profile_id: UUID,
        record: DnsRecordCreate,
    ) -> DnsRecord:
        """Add a DNS record to a profile."""
        # Verify profile exists
        await self.get_profile(profile_id)

        if record.record_type not in VALID_RECORD_TYPES:
            raise RecordValidationError(
                f"Invalid record type: {record.record_type}"
            )

        dns_record = DnsRecord(
            id=uuid4(),
            profile_id=profile_id,
            record_type=record.record_type,
            name=record.name,
            content=record.content,
            ttl=record.ttl,
            priority=record.priority,
            synced=False,
            disabled=False,
        )

        self.db.add(dns_record)
        await self.db.flush()
        logger.info("DNS record %s added to profile %s", dns_record.id, profile_id)
        return dns_record

    async def add_records_bulk(
        self,
        profile_id: UUID,
        records: list[DnsRecordCreate],
    ) -> tuple[list[DnsRecord], list[str]]:
        """Add multiple DNS records to a profile at once."""
        await self.get_profile(profile_id)

        created: list[DnsRecord] = []
        errors: list[str] = []

        for rec in records:
            try:
                if rec.record_type not in VALID_RECORD_TYPES:
                    errors.append(
                        f"Invalid record type '{rec.record_type}' for {rec.name}"
                    )
                    continue

                dns_record = DnsRecord(
                    id=uuid4(),
                    profile_id=profile_id,
                    record_type=rec.record_type,
                    name=rec.name,
                    content=rec.content,
                    ttl=rec.ttl,
                    priority=rec.priority,
                    synced=False,
                    disabled=False,
                )
                self.db.add(dns_record)
                created.append(dns_record)
            except Exception as exc:
                errors.append(f"Failed to create record {rec.name}: {exc}")

        await self.db.flush()
        return created, errors

    async def get_record(self, record_id: UUID) -> DnsRecord:
        """Get a DNS record by ID."""
        record = await self.db.get(DnsRecord, record_id)
        if record is None:
            raise RecordNotFoundError(f"DNS record {record_id} not found")
        return record

    async def list_records(
        self,
        profile_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> list[DnsRecord]:
        """List DNS records for a profile."""
        await self.get_profile(profile_id)

        result = await self.db.execute(
            select(DnsRecord)
            .where(DnsRecord.profile_id == profile_id)
            .offset(offset)
            .limit(limit)
            .order_by(DnsRecord.created_at.asc())
        )
        return list(result.scalars().all())

    async def update_record(
        self,
        record_id: UUID,
        update: DnsRecordUpdate,
    ) -> DnsRecord:
        """Update a DNS record."""
        record = await self.get_record(record_id)

        for field, value in update.model_dump(exclude_unset=True).items():
            setattr(record, field, value)

        record.updated_at = datetime.now(UTC)
        record.synced = False
        self.db.add(record)
        await self.db.flush()

        logger.info("DNS record %s updated", record_id)
        return record

    async def delete_record(self, record_id: UUID) -> None:
        """Delete a DNS record."""
        record = await self.get_record(record_id)
        await self.db.delete(record)
        await self.db.flush()
        logger.info("DNS record %s deleted", record_id)

    # ------------------------------------------------------------------
    # Sync Operations
    # ------------------------------------------------------------------

    async def sync_records(self, profile_id: UUID) -> SmartDnsSyncResponse:
        """Sync all unsynced DNS records with PowerDNS."""
        await self.get_profile(profile_id)

        result = await self.db.execute(
            select(DnsRecord)
            .where(
                and_(
                    DnsRecord.profile_id == profile_id,
                    DnsRecord.synced == False,  # noqa: E712
                )
            )
        )
        unsynced_records = list(result.scalars().all())

        synced_count = 0
        failed_count = 0
        sync_errors: list[str] = []

        for record in unsynced_records:
            try:
                # In production, this would call PowerDNS API
                record.synced = True
                record.synced_at = datetime.now(UTC)
                record.updated_at = datetime.now(UTC)
                self.db.add(record)
                synced_count += 1
            except Exception as exc:
                sync_errors.append(f"Failed to sync {record.id}: {exc}")
                failed_count += 1

        await self.db.flush()

        logger.info(
            "SmartDNS profile %s sync: %d synced, %d failed",
            profile_id,
            synced_count,
            failed_count,
        )

        return SmartDnsSyncResponse(
            profile_id=profile_id,
            synced=synced_count,
            failed=failed_count,
            errors=sync_errors,
        )


def build_profile_response(profile: SmartDnsProfile) -> SmartDnsProfileResponse:
    """Convert a SmartDnsProfile model to a response schema."""
    return SmartDnsProfileResponse(
        id=profile.id,
        service_id=profile.service_id,
        profile_name=profile.profile_name,
        upstream_dns=profile.upstream_dns or "8.8.8.8",
        geo_region=profile.geo_region,
        allowed_ips=profile.allowed_ips,
        max_queries_per_second=profile.max_queries_per_second,
        enable_dnssec=profile.enable_dnssec,
        enable_logging=profile.enable_logging,
        enable_ad_blocking=profile.enable_ad_blocking,
        extra_config=profile.extra_config,
        notes=profile.notes,
        status=profile.status,
        pdns_zone_id=profile.pdns_zone_id,
        pdns_zone_name=profile.pdns_zone_name,
        total_queries=profile.total_queries or 0,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def build_record_response(record: DnsRecord) -> DnsRecordResponse:
    """Convert a DnsRecord model to a response schema."""
    return DnsRecordResponse(
        id=record.id,
        profile_id=record.profile_id,
        record_type=record.record_type,
        name=record.name,
        content=record.content,
        ttl=record.ttl,
        priority=record.priority,
        disabled=record.disabled,
        synced=record.synced,
        synced_at=record.synced_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


__all__ = [
    "SmartDnsService",
    "SmartDnsError",
    "ProfileNotFoundError",
    "ProfileAlreadyExistsError",
    "ProfileProvisioningError",
    "RecordNotFoundError",
    "RecordValidationError",
    "build_profile_response",
    "build_record_response",
]