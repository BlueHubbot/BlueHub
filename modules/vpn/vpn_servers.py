"""
VPN Server CRUD Operations
============================
Database access layer for VpnServer model.
Handles creation, retrieval, update, deletion, and server availability queries.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select, func, and_

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class VpnServerCRUD:
    """
    CRUD operations for the VpnServer model.

    All methods are async and require an :class:`AsyncSession` from SQLAlchemy.
    """

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        name: str,
        host: str,
        public_ip: str,
        endpoint: str,
        port: int = 51820,
        private_key: str | None = None,
        public_key: str | None = None,
        country: str = "US",
        city: str | None = None,
        provider: str | None = None,
        bandwidth_limit_mbps: int | None = None,
        max_clients: int = 100,
        is_active: bool = True,
        notes: str | None = None,
    ) -> object:
        """
        Create a new VPN server record.

        Returns:
            The created VpnServer instance.
        """
        from modules.vpn.models import VpnServer

        server = VpnServer(
            name=name,
            host=host,
            port=port,
            public_ip=public_ip,
            private_key=private_key,
            public_key=public_key,
            endpoint=endpoint,
            country=country,
            city=city,
            provider=provider,
            bandwidth_limit_mbps=bandwidth_limit_mbps,
            max_clients=max_clients,
            is_active=is_active,
            notes=notes,
        )
        db.add(server)
        await db.flush()
        await db.refresh(server)
        logger.info("Created VPN server: %s (host=%s)", server.name, server.host)
        return server

    @staticmethod
    async def get(db: AsyncSession, server_id: str) -> object | None:
        """
        Retrieve a VPN server by its UUID.

        Args:
            db: Database session.
            server_id: UUID string of the server.

        Returns:
            VpnServer instance or None.
        """
        from modules.vpn.models import VpnServer

        result = await db.execute(
            select(VpnServer).where(VpnServer.id == server_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(
        db: AsyncSession,
        *,
        active_only: bool = False,
        country: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[object]:
        """
        List VPN servers with optional filtering.

        Args:
            db: Database session.
            active_only: If True, only return active servers.
            country: ISO country code filter.
            skip: Pagination offset.
            limit: Pagination limit.

        Returns:
            List of VpnServer instances.
        """
        from modules.vpn.models import VpnServer

        stmt = select(VpnServer).order_by(VpnServer.created_at.desc())

        if active_only:
            stmt = stmt.where(VpnServer.is_active.is_(True))
        if country:
            stmt = stmt.where(VpnServer.country == country)

        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_available_servers(
        db: AsyncSession,
        *,
        country: str | None = None,
        protocol: str = "wireguard",
    ) -> list[object]:
        """
        Get servers that can accept new clients.

        A server is "available" if:
        - It is active
        - Its current_clients < max_clients
        - Optionally filtered by country

        Args:
            db: Database session.
            country: Optional ISO country code filter.
            protocol: Protocol filter (reserved for future use).

        Returns:
            List of available VpnServer instances.
        """
        from modules.vpn.models import VpnServer

        stmt = (
            select(VpnServer)
            .where(
                and_(
                    VpnServer.is_active.is_(True),
                    VpnServer.current_clients < VpnServer.max_clients,
                )
            )
            .order_by(VpnServer.current_clients.asc())
        )

        if country:
            stmt = stmt.where(VpnServer.country == country)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_least_loaded_server(
        db: AsyncSession,
        *,
        country: str | None = None,
    ) -> object | None:
        """
        Get the server with the fewest current clients.

        Args:
            db: Database session.
            country: Optional country filter.

        Returns:
            VpnServer with the most free slots, or None.
        """
        from modules.vpn.models import VpnServer

        stmt = (
            select(VpnServer)
            .where(
                and_(
                    VpnServer.is_active.is_(True),
                    VpnServer.current_clients < VpnServer.max_clients,
                )
            )
            .order_by(VpnServer.current_clients.asc())
        )

        if country:
            stmt = stmt.where(VpnServer.country == country)

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update(
        db: AsyncSession,
        server_id: str,
        **kwargs: object,
    ) -> object | None:
        """
        Update a VPN server's fields.

        Args:
            db: Database session.
            server_id: UUID of the server to update.
            **kwargs: Field-value pairs to update.

        Returns:
            Updated VpnServer instance, or None if not found.
        """
        from modules.vpn.models import VpnServer

        server = await VpnServerCRUD.get(db, server_id)
        if server is None:
            return None

        allowed_fields = {
            "name", "host", "port", "public_ip", "private_key", "public_key",
            "endpoint", "country", "city", "provider", "bandwidth_limit_mbps",
            "max_clients", "current_clients", "is_active", "notes",
        }

        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(server, key, value)

        await db.flush()
        await db.refresh(server)
        logger.info("Updated VPN server %s: %s", server_id, kwargs)
        return server

    @staticmethod
    async def increment_clients(
        db: AsyncSession,
        server_id: str,
        delta: int = 1,
    ) -> object | None:
        """
        Atomically increment (or decrement) the current_clients counter.

        Args:
            db: Database session.
            server_id: UUID of the server.
            delta: Amount to change (positive to add, negative to remove).

        Returns:
            Updated VpnServer instance, or None if not found.
        """
        from modules.vpn.models import VpnServer

        server = await VpnServerCRUD.get(db, server_id)
        if server is None:
            return None

        server.current_clients = max(0, server.current_clients + delta)
        await db.flush()
        await db.refresh(server)
        return server

    @staticmethod
    async def delete(
        db: AsyncSession,
        server_id: str,
    ) -> bool:
        """
        Delete a VPN server record.

        Args:
            db: Database session.
            server_id: UUID of the server to delete.

        Returns:
            True if deleted, False if not found.
        """
        from modules.vpn.models import VpnServer

        server = await VpnServerCRUD.get(db, server_id)
        if server is None:
            return False

        await db.delete(server)
        await db.flush()
        logger.info("Deleted VPN server %s", server_id)
        return True

    @staticmethod
    async def count_active(db: AsyncSession) -> int:
        """
        Count the number of active VPN servers.

        Args:
            db: Database session.

        Returns:
            Count of active servers.
        """
        from modules.vpn.models import VpnServer

        result = await db.execute(
            select(func.count(VpnServer.id)).where(VpnServer.is_active.is_(True))
        )
        return result.scalar() or 0


__all__ = ["VpnServerCRUD"]