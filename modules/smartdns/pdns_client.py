"""
SmartDNS PowerDNS Client
=========================
HTTP client for interacting with PowerDNS Authoritative Server API.
Handles zone management, DNS record CRUD, and zone sync.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger("bluehub.modules.smartdns.pdns")


# ------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------
class PowerDnsClientError(Exception):
    """Base exception for PowerDNS client errors."""


class PowerDnsConnectionError(PowerDnsClientError):
    """Cannot connect to PowerDNS API."""


class PowerDnsZoneNotFoundError(PowerDnsClientError):
    """Requested zone does not exist in PowerDNS."""


class PowerDnsRecordError(PowerDnsClientError):
    """DNS record operation failed on PowerDNS."""


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------
@dataclass
class PdnsZone:
    """PowerDNS zone representation."""

    zone_id: str
    name: str
    kind: str  # Native, Master, Slave
    dnssec: bool
    serial: int
    records_count: int = 0


@dataclass
class PdnsRecord:
    """PowerDNS DNS record representation."""

    name: str
    type: str
    content: str
    ttl: int = 300
    priority: int = 0
    disabled: bool = False


# ------------------------------------------------------------------
# PowerDnsClient
# ------------------------------------------------------------------
class PowerDnsClient:
    """
    Async HTTP client for PowerDNS Authoritative Server API (v1).
    
    Uses httpx for HTTP communication with the PowerDNS REST API.
    Manages server-level DNS zones for SmartDNS profiles.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        server_id: str | None = None,
    ) -> None:
        self.base_url = (base_url or settings.PDNS_API_URL).rstrip("/")
        self.api_key = api_key or settings.PDNS_API_KEY
        self.server_id = server_id or settings.PDNS_SERVER_ID
        self._client: httpx.AsyncClient | None = None

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}/api/v1/servers/{self.server_id}{path}"

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    async def _get_client(self) -> httpx.AsyncClient:
        """Return or create the shared httpx AsyncClient."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self._headers,
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Zone management
    # ------------------------------------------------------------------
    async def list_zones(self) -> list[PdnsZone]:
        """List all zones on the PowerDNS server."""
        client = await self._get_client()
        try:
            resp = await client.get(self._build_url("/zones"))
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise PowerDnsConnectionError(f"Failed to list zones: {exc}") from exc

        zones: list[PdnsZone] = []
        for z in resp.json():
            zones.append(PdnsZone(
                zone_id=z.get("id", ""),
                name=z.get("name", ""),
                kind=z.get("kind", "Native"),
                dnssec=z.get("dnssec", False),
                serial=z.get("serial", 0),
                records_count=len(z.get("rrsets", [])),
            ))
        return zones

    async def create_zone(
        self,
        zone_name: str,
        nameservers: list[str] | None = None,
        kind: str = "Native",
    ) -> PdnsZone:
        """Create a new DNS zone in PowerDNS."""
        client = await self._get_client()

        ns_list = nameservers or ["ns1.bluehub.local.", "ns2.bluehub.local."]
        rrsets: list[dict[str, Any]] = [
            {
                "name": zone_name,
                "type": "SOA",
                "ttl": 3600,
                "records": [
                    {
                        "content": f"{ns_list[0]} admin.{zone_name} 1 10800 3600 604800 3600",
                        "disabled": False,
                    }
                ],
            },
            {
                "name": zone_name,
                "type": "NS",
                "ttl": 3600,
                "records": [
                    {"content": ns, "disabled": False} for ns in ns_list
                ],
            },
        ]

        payload: dict[str, Any] = {
            "name": zone_name,
            "kind": kind,
            "nameservers": ns_list,
            "rrsets": rrsets,
        }

        try:
            resp = await client.post(self._build_url("/zones"), json=payload)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise PowerDnsRecordError(f"Failed to create zone '{zone_name}': {exc}") from exc

        data = resp.json()
        return PdnsZone(
            zone_id=data.get("id", ""),
            name=data.get("name", zone_name),
            kind=data.get("kind", kind),
            dnssec=data.get("dnssec", False),
            serial=data.get("serial", 1),
            records_count=len(data.get("rrsets", [])),
        )

    async def get_zone(self, zone_name: str) -> PdnsZone:
        """Retrieve a specific zone from PowerDNS by name."""
        client = await self._get_client()
        try:
            resp = await client.get(self._build_url(f"/zones/{zone_name}"))
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise PowerDnsZoneNotFoundError(f"Zone '{zone_name}' not found.") from exc
            raise PowerDnsConnectionError(f"Failed to get zone: {exc}") from exc
        except httpx.HTTPError as exc:
            raise PowerDnsConnectionError(f"Failed to get zone: {exc}") from exc

        data = resp.json()
        return PdnsZone(
            zone_id=data.get("id", ""),
            name=data.get("name", zone_name),
            kind=data.get("kind", "Native"),
            dnssec=data.get("dnssec", False),
            serial=data.get("serial", 0),
            records_count=len(data.get("rrsets", [])),
        )

    async def delete_zone(self, zone_name: str) -> None:
        """Delete a DNS zone from PowerDNS."""
        client = await self._get_client()
        try:
            resp = await client.delete(self._build_url(f"/zones/{zone_name}"))
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise PowerDnsZoneNotFoundError(f"Zone '{zone_name}' not found.") from exc
            raise PowerDnsRecordError(f"Failed to delete zone: {exc}") from exc
        except httpx.HTTPError as exc:
            raise PowerDnsConnectionError(f"Failed to delete zone: {exc}") from exc

        logger.info("Deleted PowerDNS zone: %s", zone_name)

    # ------------------------------------------------------------------
    # Record management (via zone RRset patch)
    # ------------------------------------------------------------------
    async def _get_zone_rrsets(self, zone_name: str) -> list[dict[str, Any]]:
        """Fetch all resource record sets for a zone."""
        client = await self._get_client()
        try:
            resp = await client.get(self._build_url(f"/zones/{zone_name}"))
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise PowerDnsConnectionError(f"Failed to fetch zone: {exc}") from exc
        return resp.json().get("rrsets", [])

    async def _patch_zone_rrsets(self, zone_name: str, rrsets: list[dict[str, Any]]) -> None:
        """Replace all resource record sets for a zone."""
        client = await self._get_client()
        payload = {"rrsets": rrsets}
        try:
            resp = await client.patch(
                self._build_url(f"/zones/{zone_name}"),
                json=payload,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise PowerDnsRecordError(f"Failed to patch zone: {exc}") from exc

    async def add_record(
        self,
        zone_name: str,
        record: PdnsRecord,
    ) -> None:
        """Add a single DNS record to a zone."""
        existing = await self._get_zone_rrsets(zone_name)

        rrset_name = record.name if record.name.endswith(".") else f"{record.name}."
        if not rrset_name.endswith(f".{zone_name}") and rrset_name != zone_name:
            rrset_name = f"{rrset_name}.{zone_name}" if rrset_name != zone_name else zone_name

        # Find existing RRset for this name+type
        found = False
        for rrset in existing:
            if rrset["name"] == rrset_name and rrset["type"] == record.type:
                rrset["records"].append({
                    "content": record.content,
                    "disabled": record.disabled,
                })
                rrset["changetype"] = "REPLACE"
                found = True
                break

        if not found:
            existing.append({
                "name": rrset_name,
                "type": record.type,
                "ttl": record.ttl,
                "changetype": "REPLACE",
                "records": [
                    {
                        "content": record.content,
                        "disabled": record.disabled,
                    }
                ],
            })
            if record.priority > 0 and record.type in ("MX", "SRV"):
                existing[-1]["records"][0]["content"] = f"{record.priority} {record.content}"

        await self._patch_zone_rrsets(zone_name, existing)

    async def delete_record(
        self,
        zone_name: str,
        record_name: str,
        record_type: str,
    ) -> None:
        """Remove a DNS record from a zone."""
        existing = await self._get_zone_rrsets(zone_name)

        rrset_name = record_name if record_name.endswith(".") else f"{record_name}."
        if not rrset_name.endswith(f".{zone_name}"):
            rrset_name = f"{rrset_name}.{zone_name}"

        updated: list[dict[str, Any]] = []
        for rrset in existing:
            if rrset["name"] == rrset_name and rrset["type"] == record_type:
                rrset["changetype"] = "DELETE"
            updated.append(rrset)

        await self._patch_zone_rrsets(zone_name, updated)

    async def list_records(self, zone_name: str) -> list[PdnsRecord]:
        """List all DNS records in a zone."""
        rrsets = await self._get_zone_rrsets(zone_name)
        records: list[PdnsRecord] = []
        for rrset in rrsets:
            for rec in rrset.get("records", []):
                records.append(PdnsRecord(
                    name=rrset["name"],
                    type=rrset["type"],
                    content=rec["content"],
                    ttl=rrset.get("ttl", 300),
                    priority=0,
                    disabled=rec.get("disabled", False),
                ))
        return records

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------
    async def health_check(self) -> bool:
        """Check if PowerDNS API is reachable and responding."""
        client = await self._get_client()
        try:
            resp = await client.get(self._build_url("/zones"))
            return resp.status_code < 500
        except httpx.HTTPError:
            return False


__all__ = [
    "PowerDnsClient",
    "PowerDnsClientError",
    "PowerDnsConnectionError",
    "PowerDnsZoneNotFoundError",
    "PowerDnsRecordError",
    "PdnsZone",
    "PdnsRecord",
]
