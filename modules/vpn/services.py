"""
VPN Services Layer
==================
Business logic orchestration for VPN account lifecycle management.

This module ties together WireGuardService, XrayService, and
VpnServerService, providing high-level operations for provisioning,
suspension, termination, and traffic tracking.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from modules.vpn.models import VpnAccount, VpnProtocolConfig, VpnServer, VpnSession
from modules.vpn.vpn_servers import VpnServerService
from modules.vpn.wireguard import (
    WireGuardError,
    WireGuardKeyGenerationError,
    WireGuardService,
)
from modules.vpn.xray import (
    XrayConfigError,
    XrayService,
)
from shared.models.enums import VpnAccountStatus, VpnProtocol, VpnSessionStatus
from shared.models.service import Service, ServiceStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class VpnServiceError(Exception):
    """Base exception for VPN service operations."""


class VpnProvisioningError(VpnServiceError):
    """Raised when VPN account provisioning fails."""


class VpnSuspensionError(VpnServiceError):
    """Raised when VPN account suspension fails."""


class VpnConfigGenerationError(VpnServiceError):
    """Raised when client config generation fails."""


# ---------------------------------------------------------------------------
# Traffic Summary Dataclass
# ---------------------------------------------------------------------------


@dataclass
class AccountTrafficSummary:
    """Aggregated traffic data for a single VPN account."""

    account_id: str
    public_key: str | None
    bytes_sent: int
    bytes_received: int
    total_bytes: int
    last_handshake: datetime | None
    is_connected: bool
    active_sessions: int


# ---------------------------------------------------------------------------
# VPN Account Service
# ---------------------------------------------------------------------------


class VpnAccountService:
    """
    High-level orchestrator for VPN account lifecycle operations.

    Coordinates WireGuard, Xray, and VpnServer services with database
    persistence to provision, manage, and decommission accounts.
    """

    # Defaults
    DEFAULT_DNS = "1.1.1.1,1.0.0.1"
    DEFAULT_MTU = 1420
    DEFAULT_KEEPALIVE = 25

    # ------------------------------------------------------------------
    # Account CRUD
    # ------------------------------------------------------------------

    @staticmethod
    async def get_account(
        db: AsyncSession,
        account_id: str,
        *,
        load_relations: bool = True,
    ) -> VpnAccount | None:
        """
        Fetch a single VPN account by ID.

        Args:
            db: Database session.
            account_id: UUID of the account.
            load_relations: If True, eagerly load relationships.

        Returns:
            VpnAccount or None.
        """
        stmt = select(VpnAccount).where(VpnAccount.id == account_id)
        if load_relations:
            stmt = stmt.options(
                selectinload(VpnAccount.service),
                selectinload(VpnAccount.sessions),
                selectinload(VpnAccount.protocol_configs),
                selectinload(VpnAccount.server_rel),
            )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def list_accounts(
        db: AsyncSession,
        *,
        service_id: str | None = None,
        protocol: VpnProtocol | None = None,
        status: VpnAccountStatus | None = None,
        server_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[VpnAccount], int]:
        """
        List VPN accounts with optional filters.

        Args:
            db: Database session.
            service_id: Filter by associated service.
            protocol: Filter by protocol.
            status: Filter by account status.
            server_id: Filter by assigned server.
            offset: Pagination offset.
            limit: Max results.

        Returns:
            Tuple of (accounts, total_count).
        """
        conditions = []
        if service_id:
            conditions.append(VpnAccount.service_id == service_id)
        if protocol:
            conditions.append(VpnAccount.protocol == protocol)
        if status:
            conditions.append(VpnAccount.status == status)
        if server_id:
            conditions.append(VpnAccount.server_id == server_id)

        count_stmt = select(func.count(VpnAccount.id))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(VpnAccount)
            .options(
                selectinload(VpnAccount.service),
                selectinload(VpnAccount.server_rel),
            )
            .order_by(VpnAccount.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if conditions:
            stmt = stmt.where(*conditions)

        result = await db.execute(stmt)
        accounts = list(result.scalars().all())
        return accounts, total

    # ------------------------------------------------------------------
    # Provisioning
    # ------------------------------------------------------------------

    @staticmethod
    async def create_account(
        db: AsyncSession,
        *,
        service_id: str,
        protocol: VpnProtocol = VpnProtocol.WIREGUARD,
        server_id: str | None = None,
        assigned_ip: str | None = None,
        dns_servers: str | None = None,
        allowed_ips: str | None = None,
        bandwidth_limit_bytes: int | None = None,
        max_connections: int = 3,
        notes: str | None = None,
        protocol_configs: dict[str, Any] | None = None,
    ) -> VpnAccount:
        """
        Provision a new VPN account for a service.

        Generates keys, assigns to a server, creates protocol configs,
        and stores everything in the database.

        Args:
            db: Database session.
            service_id: UUID of the associated Service.
            protocol: VPN protocol to use.
            server_id: Target VPN server UUID. Auto-assigned if None.
            assigned_ip: VPN IP address for the client.
            dns_servers: Comma-separated DNS servers.
            allowed_ips: Comma-separated allowed IP ranges.
            bandwidth_limit_bytes: Bandwidth limit in bytes.
            max_connections: Max concurrent connections.
            notes: Admin notes.
            protocol_configs: Extra protocol-specific key-value configs.

        Returns:
            The newly created VpnAccount.

        Raises:
            VpnProvisioningError: If provisioning fails.
        """
        # --- Validate service exists and is active ---
        service = await db.get(Service, service_id)
        if not service:
            raise VpnProvisioningError(f"Service {service_id} not found")
        if service.status == ServiceStatus.CANCELLED:
            raise VpnProvisioningError(
                f"Cannot provision account for cancelled service {service_id}"
            )

        # --- Auto-assign server if not specified ---
        if server_id is None:
            server = await VpnServerService.assign_server(
                db, protocol=protocol
            )
            if server is None:
                raise VpnProvisioningError(
                    f"No active VPN server available for protocol {protocol.value}"
                )
            server_id = str(server.id)
        else:
            server = await db.get(VpnServer, server_id)
            if not server or not server.is_active:
                raise VpnProvisioningError(
                    f"Server {server_id} not found or inactive"
                )

        # --- Generate protocol-specific keys and config ---
        dns = dns_servers or VpnAccountService.DEFAULT_DNS
        try:
            if protocol == VpnProtocol.WIREGUARD:
                provisioning_data = await VpnAccountService._provision_wireguard(
                    db=db,
                    server=server,
                    assigned_ip=assigned_ip,
                    dns_servers=dns,
                    allowed_ips=allowed_ips,
                )
            elif protocol in (
                VpnProtocol.VLESS,
                VpnProtocol.TROJAN,
                VpnProtocol.SHADOWSOCKS,
            ):
                provisioning_data = await VpnAccountService._provision_xray(
                    db=db,
                    server=server,
                    protocol=protocol,
                    assigned_ip=assigned_ip,
                    dns_servers=dns,
                    allowed_ips=allowed_ips,
                    protocol_configs=protocol_configs or {},
                )
            else:
                raise VpnProvisioningError(
                    f"Unsupported protocol: {protocol.value}"
                )
        except (WireGuardError, WireGuardKeyGenerationError, XrayConfigError) as exc:
            raise VpnProvisioningError(
                f"Key/config generation failed for {protocol.value}: {exc}"
            ) from exc

        # --- Create account record ---
        account_id = str(uuid4())
        now = datetime.now(tz=UTC)

        account = VpnAccount(
            id=account_id,
            service_id=service_id,
            protocol=protocol,
            status=VpnAccountStatus.ACTIVE,
            assigned_ip=provisioning_data.get("assigned_ip"),
            dns_servers=dns,
            allowed_ips=provisioning_data.get("allowed_ips"),
            bandwidth_limit_bytes=bandwidth_limit_bytes,
            max_connections=max_connections,
            server_id=server_id,
            public_key=provisioning_data.get("public_key"),
            private_key=provisioning_data.get("private_key"),
            preshared_key=provisioning_data.get("preshared_key"),
            client_config=provisioning_data.get("client_config"),
            provisioned_at=now,
            total_bytes=0,
            notes=notes,
        )
        db.add(account)

        # --- Store protocol-specific configs ---
        for key, value in (protocol_configs or {}).items():
            db.add(
                VpnProtocolConfig(
                    vpn_account_id=account_id,
                    config_key=key,
                    config_value=json.dumps(value) if not isinstance(value, str) else value,
                )
            )

        # --- Add extra configs from provisioning ---
        extra_keys = {"sni", "flow", "network", "security", "fingerprint", "spiderx"}
        for ek in extra_keys:
            if ek in provisioning_data:
                db.add(
                    VpnProtocolConfig(
                        vpn_account_id=account_id,
                        config_key=ek,
                        config_value=str(provisioning_data[ek]),
                    )
                )

        # --- Bump server client count ---
        if server.current_clients is not None:
            server.current_clients += 1

        await db.commit()
        await db.refresh(account)

        logger.info(
            "Provisioned %s account %s for service %s on server %s",
            protocol.value,
            account_id,
            service_id,
            server_id,
        )
        return account

    # ------------------------------------------------------------------
    # Protocol-Specific Provisioning Helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _provision_wireguard(
        db: AsyncSession,
        server: VpnServer,
        assigned_ip: str | None = None,
        dns_servers: str = DEFAULT_DNS,
        allowed_ips: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate WireGuard keys and client configuration.

        Args:
            db: Database session.
            server: Target VpnServer.
            assigned_ip: Client IP (auto-generated if None).
            dns_servers: DNS servers for client config.
            allowed_ips: Allowed IP ranges.

        Returns:
            Dict with keys, IPs, and client config.
        """
        key_pair = WireGuardService.generate_key_pair()

        # Auto-assign IP if not provided
        if assigned_ip is None:
            assigned_ip = await VpnAccountService._next_wireguard_ip(db, server.id)

        default_allowed = "0.0.0.0/0,::/0"
        final_allowed = allowed_ips or default_allowed

        # Build peer config block
        peer_config = WireGuardService.generate_peer_config(
            server=server,
            account_public_key=key_pair.public_key,
            assigned_ip=assigned_ip,
            preshared_key=None,  # generated separately if needed
            dns_servers=dns_servers,
            mtu=VpnAccountService.DEFAULT_MTU,
            keepalive=VpnAccountService.DEFAULT_KEEPALIVE,
            allowed_ips=final_allowed,
        )

        # Build full client config (Interface + Peer sections)
        host_port = f"{server.public_ip}:{server.port}"
        client_config = (
            "[Interface]\n"
            f"PrivateKey = {key_pair.private_key}\n"
            f"Address = {assigned_ip}\n"
            f"DNS = {dns_servers}\n"
            f"MTU = {VpnAccountService.DEFAULT_MTU}\n"
            "\n"
            "[Peer]\n"
            f"PublicKey = {server.public_key or ''}\n"
            f"Endpoint = {host_port}\n"
            f"AllowedIPs = {final_allowed}\n"
            f"PersistentKeepalive = {VpnAccountService.DEFAULT_KEEPALIVE}\n"
        )

        return {
            "assigned_ip": assigned_ip,
            "allowed_ips": final_allowed,
            "public_key": key_pair.public_key,
            "private_key": key_pair.private_key,
            "client_config": client_config,
            "peer_config": peer_config,
        }

    @staticmethod
    async def _provision_xray(
        db: AsyncSession,
        server: VpnServer,
        protocol: VpnProtocol,
        assigned_ip: str | None = None,
        dns_servers: str = DEFAULT_DNS,
        allowed_ips: str | None = None,
        protocol_configs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate Xray keys and client configuration.

        Args:
            db: Database session.
            server: Target VpnServer.
            protocol: Xray-based protocol (vless, trojan, shadowsocks).
            assigned_ip: Client IP (not used by Xray, kept for schema).
            dns_servers: DNS servers.
            allowed_ips: Allowed IP ranges.
            protocol_configs: Extra protocol settings.

        Returns:
            Dict with keys and client config link.
        """
        configs = protocol_configs or {}

        if protocol == VpnProtocol.VLESS:
            # Generate VLESS Reality keys
            key_pair = XrayService.generate_vless_keys()
            user_id = key_pair.uuid
            public_key_str = user_id
            private_key_str = user_id  # VLESS uses UUID as the "key"

            # Build Xray config on the server side (add user to server config)
            flow = configs.get("flow", XrayService.DEFAULT_FLOW)
            sni = configs.get("sni", "")
            network = configs.get("network", "tcp")
            security = configs.get("security", "reality")
            fingerprint = configs.get("fingerprint", "chrome")
            spiderx = configs.get("spiderx", "")

            client_config = VpnAccountService._generate_vless_client_link(
                uuid=user_id,
                host=server.public_ip,
                port=443,
                flow=flow,
                sni=sni,
                network=network,
                security=security,
                fingerprint=fingerprint,
                spiderx=spiderx,
                remark=f"bluehub-{user_id[:8]}",
            )

            result = {
                "assigned_ip": None,
                "allowed_ips": allowed_ips or "0.0.0.0/0",
                "public_key": public_key_str,
                "private_key": private_key_str,
                "client_config": client_config,
                "sni": sni,
                "flow": flow,
                "network": network,
                "security": security,
                "fingerprint": fingerprint,
                "spiderx": spiderx,
            }

        elif protocol == VpnProtocol.TROJAN:
            # Trojan uses password-based auth
            password = XrayService.generate_trojan_password()
            sni = configs.get("sni", "")
            client_config = VpnAccountService._generate_trojan_client_link(
                password=password,
                host=server.public_ip,
                port=443,
                sni=sni,
                remark=f"bluehub-{uuid4().hex[:8]}",
            )
            result = {
                "assigned_ip": None,
                "allowed_ips": allowed_ips or "0.0.0.0/0",
                "public_key": password,
                "private_key": password,
                "client_config": client_config,
                "sni": sni,
            }

        elif protocol == VpnProtocol.SHADOWSOCKS:
            # Shadowsocks uses method:password auth
            method = configs.get("method", "aes-256-gcm")
            password = XrayService.generate_trojan_password()
            client_config = VpnAccountService._generate_shadowsocks_client_config(
                method=method,
                password=password,
                host=server.public_ip,
                port=8388,
                remark=f"bluehub-{uuid4().hex[:8]}",
            )
            result = {
                "assigned_ip": None,
                "allowed_ips": allowed_ips or "0.0.0.0/0",
                "public_key": password,
                "private_key": password,
                "client_config": client_config,
                "method": method,
            }

        else:
            raise VpnProvisioningError(f"Unsupported Xray protocol: {protocol.value}")

        # If server already has Xray config, add user to it in-memory
        server_config = None
        if server.xray_config:
            try:
                server_config = json.loads(server.xray_config)
                if protocol == VpnProtocol.VLESS:
                    XrayService.add_user_via_config(
                        user_id=result["public_key"],
                        email=f"service-{uuid4().hex[:12]}",
                        flow=configs.get("flow", XrayService.DEFAULT_FLOW),
                        config_data=server_config,
                    )
            except json.JSONDecodeError:
                pass

        return result

    # ------------------------------------------------------------------
    # IP Assignment
    # ------------------------------------------------------------------

    @staticmethod
    async def _next_wireguard_ip(
        db: AsyncSession,
        server_id: str,
        subnet_base: str = "10.0.0",
        start_octet: int = 2,
        max_octet: int = 254,
    ) -> str:
        """
        Generate the next available WireGuard IP for a server.

        Scans existing accounts on the server to find an unused IP.

        Args:
            db: Database session.
            server_id: Server UUID.
            subnet_base: First three octets of the subnet.
            start_octet: Starting fourth octet.
            max_octet: Maximum fourth octet.

        Returns:
            Unused IP address string.
        """
        stmt = select(VpnAccount.assigned_ip).where(
            VpnAccount.server_id == server_id,
            VpnAccount.protocol == VpnProtocol.WIREGUARD,
            VpnAccount.assigned_ip.isnot(None),
        )
        result = await db.execute(stmt)
        used_ips = {row[0] for row in result.all() if row[0]}

        for octet in range(start_octet, max_octet + 1):
            candidate = f"{subnet_base}.{octet}"
            if f"{candidate}/32" not in used_ips and candidate not in used_ips:
                return candidate

        raise VpnProvisioningError(
            f"No available IPs in {subnet_base}.x range for server {server_id}"
        )

    # ------------------------------------------------------------------
    # Client Config Link Generators
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_vless_client_link(
        uuid: str,
        host: str,
        port: int = 443,
        flow: str = "xtls-rprx-vision",
        sni: str = "",
        network: str = "tcp",
        security: str = "reality",
        fingerprint: str = "chrome",
        spiderx: str = "",
        remark: str = "",
    ) -> str:
        """Generate a VLESS share link (vless://...) for client import."""
        import urllib.parse

        params = {
            "type": network,
            "security": security,
            "flow": flow,
            "fp": fingerprint,
        }
        if sni:
            params["sni"] = sni
        if spiderx:
            params["spx"] = spiderx

        query = urllib.parse.urlencode(params)
        remark_enc = urllib.parse.quote(remark) if remark else ""
        link = f"vless://{uuid}@{host}:{port}?{query}"
        if remark_enc:
            link += f"#{remark_enc}"
        return link

    @staticmethod
    def _generate_trojan_client_link(
        password: str,
        host: str,
        port: int = 443,
        sni: str = "",
        remark: str = "",
    ) -> str:
        """Generate a Trojan share link (trojan://...) for client import."""
        import urllib.parse

        params = {}
        if sni:
            params["sni"] = sni

        query = urllib.parse.urlencode(params) if params else ""
        remark_enc = urllib.parse.quote(remark) if remark else ""
        link = f"trojan://{urllib.parse.quote(password)}@{host}:{port}"
        if query:
            link += f"?{query}"
        if remark_enc:
            link += f"#{remark_enc}"
        return link

    @staticmethod
    def _generate_shadowsocks_client_config(
        method: str,
        password: str,
        host: str,
        port: int = 8388,
        remark: str = "",
    ) -> str:
        """Generate a Shadowsocks SIP002 URI for client import."""
        import base64
        import urllib.parse

        # SIP002 format: ss://base64(method:password)@host:port#remark
        userinfo = base64.urlsafe_b64encode(
            f"{method}:{password}".encode()
        ).decode().rstrip("=")
        link = f"ss://{userinfo}@{host}:{port}"
        if remark:
            link += f"#{urllib.parse.quote(remark)}"
        return link

    # ------------------------------------------------------------------
    # Suspension / Unsuspension
    # ------------------------------------------------------------------

    @staticmethod
    async def suspend_account(
        db: AsyncSession,
        account: VpnAccount,
        *,
        reason: str = "manual",
    ) -> VpnAccount:
        """
        Suspend a VPN account.

        Removes the peer from the WireGuard interface or marks as suspended
        for Xray-based protocols. Updates database status.

        Args:
            db: Database session.
            account: VpnAccount to suspend.
            reason: Reason for suspension.

        Returns:
            Updated VpnAccount.

        Raises:
            VpnSuspensionError: If suspension fails.
        """
        if account.status == VpnAccountStatus.SUSPENDED:
            return account

        server = account.server_rel
        if server and account.status == VpnAccountStatus.ACTIVE:
            try:
                if account.protocol == VpnProtocol.WIREGUARD:
                    WireGuardService.remove_peer_from_server(server, account)
                # Xray-based protocols: nothing to remove at kernel level;
                # traffic for this UUID simply won't be accepted after
                # syncing the config without this user.
            except WireGuardError as exc:
                logger.warning(
                    "WireGuard peer removal failed (non-fatal): %s", exc
                )

        account.status = VpnAccountStatus.SUSPENDED
        account.updated_at = datetime.now(tz=UTC)
        account.notes = (
            f"{account.notes or ''}\n[SUSPENDED {datetime.now(tz=UTC).isoformat()}] {reason}"
        ).strip()

        # End all active sessions
        await db.execute(
            update(VpnSession)
            .where(
                VpnSession.vpn_account_id == account.id,
                VpnSession.status == VpnSessionStatus.CONNECTED,
            )
            .values(
                status=VpnSessionStatus.DISCONNECTED,
                disconnected_at=datetime.now(tz=UTC),
                disconnect_reason=f"suspension: {reason}",
            )
        )

        await db.commit()
        await db.refresh(account)

        logger.info(
            "Suspended VPN account %s (protocol=%s, reason=%s)",
            account.id,
            account.protocol.value,
            reason,
        )
        return account

    @staticmethod
    async def unsuspend_account(
        db: AsyncSession,
        account: VpnAccount,
        *,
        reason: str = "manual",
    ) -> VpnAccount:
        """
        Re-activate a suspended VPN account.

        Re-adds the peer to the WireGuard interface or marks as active
        for Xray-based protocols.

        Args:
            db: Database session.
            account: VpnAccount to unsuspend.
            reason: Reason for unsuspension.

        Returns:
            Updated VpnAccount.

        Raises:
            VpnServiceError: If unsuspension fails.
        """
        if account.status != VpnAccountStatus.SUSPENDED:
            return account

        server = account.server_rel
        if server:
            try:
                if account.protocol == VpnProtocol.WIREGUARD:
                    WireGuardService.restore_peer(server, account)
            except WireGuardError as exc:
                raise VpnServiceError(
                    f"Failed to restore WireGuard peer: {exc}"
                ) from exc

        account.status = VpnAccountStatus.ACTIVE
        account.updated_at = datetime.now(tz=UTC)
        account.notes = (
            f"{account.notes or ''}\n[UNSUSPENDED {datetime.now(tz=UTC).isoformat()}] {reason}"
        ).strip()

        await db.commit()
        await db.refresh(account)

        logger.info(
            "Unsuspended VPN account %s (protocol=%s)",
            account.id,
            account.protocol.value,
        )
        return account

    # ------------------------------------------------------------------
    # Termination
    # ------------------------------------------------------------------

    @staticmethod
    async def terminate_account(
        db: AsyncSession,
        account: VpnAccount,
        *,
        reason: str = "service_cancelled",
    ) -> VpnAccount:
        """
        Permanently decommission a VPN account.

        Removes peer from server, ends all sessions, and marks as terminated.

        Args:
            db: Database session.
            account: VpnAccount to terminate.
            reason: Reason for termination.

        Returns:
            Updated VpnAccount.
        """
        if account.status == VpnAccountStatus.CANCELLED:
            return account

        server = account.server_rel
        if server and account.status in (
            VpnAccountStatus.ACTIVE,
            VpnAccountStatus.SUSPENDED,
        ):
            try:
                if account.protocol == VpnProtocol.WIREGUARD:
                    WireGuardService.remove_peer_from_server(server, account)
            except WireGuardError as exc:
                logger.warning(
                    "WireGuard peer removal during termination failed: %s", exc
                )

            # Decrement server client count
            if server.current_clients is not None and server.current_clients > 0:
                server.current_clients -= 1

        account.status = VpnAccountStatus.CANCELLED
        account.updated_at = datetime.now(tz=UTC)
        account.notes = (
            f"{account.notes or ''}\n[TERMINATED {datetime.now(tz=UTC).isoformat()}] {reason}"
        ).strip()

        # End all active sessions
        now = datetime.now(tz=UTC)
        await db.execute(
            update(VpnSession)
            .where(
                VpnSession.vpn_account_id == account.id,
                VpnSession.status == VpnSessionStatus.CONNECTED,
            )
            .values(
                status=VpnSessionStatus.DISCONNECTED,
                disconnected_at=now,
                disconnect_reason=f"termination: {reason}",
            )
        )

        await db.commit()
        await db.refresh(account)

        logger.info(
            "Terminated VPN account %s (protocol=%s, reason=%s)",
            account.id,
            account.protocol.value,
            reason,
        )
        return account

    # ------------------------------------------------------------------
    # Client Config Regeneration
    # ------------------------------------------------------------------

    @staticmethod
    def regenerate_client_config(account: VpnAccount) -> str:
        """
        Regenerate the client configuration string for an account.

        Args:
            account: VpnAccount with provisioning data populated.

        Returns:
            Client configuration text or share link.

        Raises:
            VpnConfigGenerationError: If config cannot be regenerated.
        """
        if not account.server_rel:
            raise VpnConfigGenerationError(
                f"No server assigned to account {account.id}"
            )

        server = account.server_rel
        dns = account.dns_servers or VpnAccountService.DEFAULT_DNS

        if account.protocol == VpnProtocol.WIREGUARD:
            if not account.public_key or not account.private_key:
                raise VpnConfigGenerationError(
                    "WireGuard account missing key material"
                )
            host_port = f"{server.public_ip}:{server.port}"
            allowed = account.allowed_ips or "0.0.0.0/0,::/0"
            return (
                "[Interface]\n"
                f"PrivateKey = {account.private_key}\n"
                f"Address = {account.assigned_ip or '10.0.0.2/32'}\n"
                f"DNS = {dns}\n"
                f"MTU = {VpnAccountService.DEFAULT_MTU}\n"
                "\n"
                "[Peer]\n"
                f"PublicKey = {server.public_key or ''}\n"
                f"Endpoint = {host_port}\n"
                f"AllowedIPs = {allowed}\n"
                f"PersistentKeepalive = {VpnAccountService.DEFAULT_KEEPALIVE}\n"
            )

        elif account.protocol == VpnProtocol.VLESS:
            if not account.public_key:
                raise VpnConfigGenerationError("VLESS account missing UUID")
            configs = VpnAccountService._get_protocol_configs_dict(account)
            return VpnAccountService._generate_vless_client_link(
                uuid=account.public_key,
                host=server.public_ip,
                port=443,
                flow=configs.get("flow", XrayService.DEFAULT_FLOW),
                sni=configs.get("sni", ""),
                network=configs.get("network", "tcp"),
                security=configs.get("security", "reality"),
                fingerprint=configs.get("fingerprint", "chrome"),
                spiderx=configs.get("spiderx", ""),
                remark=f"bluehub-{account.public_key[:8]}",
            )

        elif account.protocol == VpnProtocol.TROJAN:
            return VpnAccountService._generate_trojan_client_link(
                password=account.public_key or "",
                host=server.public_ip,
                port=443,
                sni=VpnAccountService._get_protocol_configs_dict(account).get(
                    "sni", ""
                ),
                remark=f"bluehub-{account.id[:8]}",
            )

        elif account.protocol == VpnProtocol.SHADOWSOCKS:
            configs = VpnAccountService._get_protocol_configs_dict(account)
            return VpnAccountService._generate_shadowsocks_client_config(
                method=configs.get("method", "aes-256-gcm"),
                password=account.public_key or "",
                host=server.public_ip,
                port=8388,
                remark=f"bluehub-{account.id[:8]}",
            )

        raise VpnConfigGenerationError(
            f"Unsupported protocol: {account.protocol.value}"
        )

    @staticmethod
    def _get_protocol_configs_dict(account: VpnAccount) -> dict[str, str]:
        """Extract protocol configs as a flat dict."""
        result: dict[str, str] = {}
        for cfg in account.protocol_configs or []:
            result[cfg.config_key] = cfg.config_value
        return result

    # ------------------------------------------------------------------
    # Traffic Tracking
    # ------------------------------------------------------------------

    @staticmethod
    async def poll_account_traffic(
        db: AsyncSession,
        account: VpnAccount,
        *,
        interface: str = "wg0",
    ) -> AccountTrafficSummary | None:
        """
        Poll traffic data for a single account and update its totals.

        Args:
            db: Database session.
            account: VpnAccount to poll.
            interface: WireGuard interface name (WG only).

        Returns:
            AccountTrafficSummary or None if polling failed.
        """
        if account.protocol != VpnProtocol.WIREGUARD:
            # Xray traffic requires API polling; stub for now
            return AccountTrafficSummary(
                account_id=account.id,
                public_key=account.public_key,
                bytes_sent=0,
                bytes_received=0,
                total_bytes=account.total_bytes or 0,
                last_handshake=None,
                is_connected=False,
                active_sessions=0,
            )

        traffic = WireGuardService.poll_account_traffic(
            account, interface=interface
        )
        if traffic is None:
            return None

        # Update cumulative totals
        session_bytes = traffic.transfer_rx + traffic.transfer_tx
        if account.total_bytes is not None:
            account.total_bytes += session_bytes
        else:
            account.total_bytes = session_bytes

        account.last_handshake_at = traffic.last_handshake
        account.updated_at = datetime.now(tz=UTC)
        await db.commit()

        # Count active sessions
        active_count_result = await db.execute(
            select(func.count(VpnSession.id)).where(
                VpnSession.vpn_account_id == account.id,
                VpnSession.status == VpnSessionStatus.CONNECTED,
            )
        )
        active_sessions = active_count_result.scalar() or 0

        is_connected = WireGuardService.is_peer_connected(
            account.public_key or "", interface=interface
        )

        return AccountTrafficSummary(
            account_id=account.id,
            public_key=account.public_key,
            bytes_sent=traffic.transfer_tx,
            bytes_received=traffic.transfer_rx,
            total_bytes=account.total_bytes or 0,
            last_handshake=traffic.last_handshake,
            is_connected=is_connected,
            active_sessions=active_sessions,
        )

    @staticmethod
    async def poll_all_accounts_traffic(
        db: AsyncSession,
        *,
        protocol: VpnProtocol = VpnProtocol.WIREGUARD,
        interface: str = "wg0",
    ) -> list[AccountTrafficSummary]:
        """
        Poll traffic for all active accounts of a given protocol.

        Args:
            db: Database session.
            protocol: Protocol to poll (WG uses wg dump, Xray uses API).
            interface: WireGuard interface name.

        Returns:
            List of AccountTrafficSummary for successfully polled accounts.
        """
        stmt = select(VpnAccount).options(
            selectinload(VpnAccount.server_rel),
            selectinload(VpnAccount.sessions),
            selectinload(VpnAccount.protocol_configs),
        ).where(
            VpnAccount.protocol == protocol,
            VpnAccount.status == VpnAccountStatus.ACTIVE,
        )
        result = await db.execute(stmt)
        accounts = result.scalars().all()

        summaries: list[AccountTrafficSummary] = []
        for account in accounts:
            try:
                summary = await VpnAccountService.poll_account_traffic(
                    db, account, interface=interface
                )
                if summary is not None:
                    summaries.append(summary)
            except Exception as exc:
                logger.warning(
                    "Failed to poll traffic for account %s: %s",
                    account.id,
                    exc,
                )

        return summaries

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    @staticmethod
    async def detect_and_sync_connections(
        db: AsyncSession,
        *,
        protocol: VpnProtocol = VpnProtocol.WIREGUARD,
        interface: str = "wg0",
    ) -> dict[str, bool]:
        """
        Detect active connections and sync session records.

        Connects peers that have recent handshakes but no active session,
        and disconnects peers whose sessions are stale.

        Args:
            db: Database session.
            protocol: Protocol to scan.
            interface: WireGuard interface name.

        Returns:
            Dict mapping account_id -> is_connected.
        """
        if protocol != VpnProtocol.WIREGUARD:
            logger.warning("Connection detection is currently WireGuard-only")
            return {}

        connections = WireGuardService.detect_connections(interface=interface)
        now = datetime.now(tz=UTC)

        # Get all active WG accounts with their public keys
        stmt = (
            select(VpnAccount)
            .options(selectinload(VpnAccount.sessions))
            .where(
                VpnAccount.protocol == VpnProtocol.WIREGUARD,
                VpnAccount.status == VpnAccountStatus.ACTIVE,
                VpnAccount.public_key.isnot(None),
            )
        )
        result = await db.execute(stmt)
        accounts = result.scalars().all()

        account_by_key: dict[str, VpnAccount] = {}
        for acc in accounts:
            if acc.public_key:
                account_by_key[acc.public_key] = acc

        result_map: dict[str, bool] = {}
        for pubkey, is_connected in connections.items():
            account = account_by_key.get(pubkey)
            if account is None:
                continue

            result_map[account.id] = is_connected

            active_session = next(
                (
                    s
                    for s in (account.sessions or [])
                    if s.status == VpnSessionStatus.CONNECTED
                ),
                None,
            )

            if is_connected and active_session is None:
                # Create new session record
                session = VpnSession(
                    id=str(uuid4()),
                    vpn_account_id=account.id,
                    status=VpnSessionStatus.CONNECTED,
                    connected_at=now,
                    client_ip=None,
                    server_endpoint=f"{account.server_rel.public_ip}:{account.server_rel.port}"
                    if account.server_rel
                    else None,
                )
                db.add(session)
                logger.info("New session created for account %s", account.id)

            elif not is_connected and active_session is not None:
                # End stale session
                active_session.status = VpnSessionStatus.DISCONNECTED
                active_session.disconnected_at = now
                active_session.disconnect_reason = "handshake_timeout"
                logger.info(
                    "Session ended for account %s (handshake timeout)",
                    account.id,
                )

        await db.commit()
        return result_map


__all__ = [
    "AccountTrafficSummary",
    "VpnAccountService",
    "VpnConfigGenerationError",
    "VpnProvisioningError",
    "VpnServiceError",
    "VpnSuspensionError",
]
