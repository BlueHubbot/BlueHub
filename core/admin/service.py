"""
BlueHub Admin Service
======================
Service layer for admin dashboard, tenant management, product management,
user management, and abuse report handling.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.admin.schemas import ProductCreate, ProductUpdate, TenantCreate, TenantUpdate
from shared.models.abuse_report import AbuseReport
from shared.models.enums import AbuseReportStatus
from shared.models.product import Product
from shared.models.service import Service
from shared.models.tenant import Tenant
from shared.models.user import User


class TenantNotFoundError(Exception):
    """Raised when a tenant is not found."""


class DuplicateTenantDomainError(Exception):
    """Raised when a tenant with the same domain exists."""


class ProductNotFoundError(Exception):
    """Raised when a product is not found."""


class DuplicateProductKeyError(Exception):
    """Raised when a product with the same key exists."""


class AbuseReportNotFoundError(Exception):
    """Raised when an abuse report is not found."""


def generate_license_key() -> str:
    """Generate a cryptographically secure license key."""
    return f"BLUEHUB-{secrets.token_hex(16).upper()}"


class AdminService:
    """Service for admin dashboard operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Dashboard Stats ──────────────────────────────────────────────────────

    async def get_dashboard_stats(self) -> dict:
        """
        Get aggregated dashboard statistics.

        Returns:
            A dictionary of dashboard statistics.
        """
        # User counts
        total_users_result = await self.session.execute(
            select(func.count(User.id))
        )
        total_users = total_users_result.scalar() or 0

        active_users_result = await self.session.execute(
            select(func.count(User.id)).where(User.is_active)
        )
        active_users = active_users_result.scalar() or 0

        # Tenant counts
        total_tenants_result = await self.session.execute(
            select(func.count(Tenant.id))
        )
        total_tenants = total_tenants_result.scalar() or 0

        active_tenants_result = await self.session.execute(
            select(func.count(Tenant.id)).where(Tenant.active)
        )
        active_tenants = active_tenants_result.scalar() or 0

        # Product counts
        total_products_result = await self.session.execute(
            select(func.count(Product.id))
        )
        total_products = total_products_result.scalar() or 0

        # Service counts
        total_services_result = await self.session.execute(
            select(func.count(Service.id))
        )
        total_services = total_services_result.scalar() or 0

        active_services_result = await self.session.execute(
            select(func.count(Service.id)).where(
                Service.status == "active"
            )
        )
        active_services = active_services_result.scalar() or 0

        # Abuse report counts
        pending_abuse_result = await self.session.execute(
            select(func.count(AbuseReport.id)).where(
                AbuseReport.status == AbuseReportStatus.PENDING.value
            )
        )
        pending_abuse = pending_abuse_result.scalar() or 0

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_tenants": total_tenants,
            "active_tenants": active_tenants,
            "total_products": total_products,
            "total_services": total_services,
            "active_services": active_services,
            "pending_abuse_reports": pending_abuse,
        }

    # ── Tenant CRUD ──────────────────────────────────────────────────────────

    async def list_tenants(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        active: bool | None = None,
    ) -> tuple[list[Tenant], int]:
        """
        List tenants with pagination and optional filters.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            search: Optional search string for name or domain.
            active: Optional active status filter.

        Returns:
            A tuple of (list of Tenant instances, total count).
        """
        query = select(Tenant)
        count_query = select(func.count(Tenant.id))

        if active is not None:
            query = query.where(Tenant.active == active)
            count_query = count_query.where(Tenant.active == active)

        if search:
            pattern = f"%{search}%"
            query = query.where(
                Tenant.name.ilike(pattern) | Tenant.domain.ilike(pattern)
            )
            count_query = count_query.where(
                Tenant.name.ilike(pattern) | Tenant.domain.ilike(pattern)
            )

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.order_by(Tenant.created_at.desc()).offset(offset).limit(page_size)

        result = await self.session.execute(query)
        tenants = list(result.unique().scalars().all())

        return tenants, total

    async def get_tenant(self, tenant_id: str) -> Tenant:
        """
        Get a tenant by ID.

        Args:
            tenant_id: The UUID of the tenant.

        Returns:
            The Tenant instance.

        Raises:
            TenantNotFoundError: If the tenant is not found.
        """
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.session.execute(stmt)
        tenant = result.unique().scalar_one_or_none()
        if not tenant:
            msg = f"Tenant with id '{tenant_id}' not found"
            raise TenantNotFoundError(msg)
        return tenant

    async def create_tenant(self, data: TenantCreate) -> Tenant:
        """
        Create a new tenant.

        Args:
            data: Tenant creation data.

        Returns:
            The newly created Tenant instance.

        Raises:
            DuplicateTenantDomainError: If the domain already exists.
        """
        # Check for duplicate domain
        existing = await self.session.execute(
            select(Tenant).where(Tenant.domain == data.domain)
        )
        if existing.unique().scalar_one_or_none():
            msg = f"Tenant with domain '{data.domain}' already exists"
            raise DuplicateTenantDomainError(msg)

        tenant = Tenant(
            name=data.name,
            domain=data.domain,
            logo_url=data.logo_url,
            branding_config=data.branding_config or {},
            telegram_bot_token=data.telegram_bot_token,
            license_key=data.license_key,
            signature=data.signature,
            active=data.active,
        )
        self.session.add(tenant)
        await self.session.flush()
        await self.session.refresh(tenant)
        return tenant

    async def update_tenant(self, tenant_id: str, data: TenantUpdate) -> Tenant:
        """
        Update a tenant.

        Args:
            tenant_id: The UUID of the tenant.
            data: The fields to update.

        Returns:
            The updated Tenant instance.

        Raises:
            TenantNotFoundError: If the tenant is not found.
        """
        tenant = await self.get_tenant(tenant_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)

        await self.session.flush()
        await self.session.refresh(tenant)
        return tenant

    async def delete_tenant(self, tenant_id: str) -> None:
        """
        Soft-delete a tenant by setting them inactive.

        Args:
            tenant_id: The UUID of the tenant.

        Raises:
            TenantNotFoundError: If the tenant is not found.
        """
        tenant = await self.get_tenant(tenant_id)
        tenant.active = False
        await self.session.flush()

    async def hard_delete_tenant(self, tenant_id: str) -> None:
        """
        Permanently delete a tenant.

        Args:
            tenant_id: The UUID of the tenant.

        Raises:
            TenantNotFoundError: If the tenant is not found.
        """
        tenant = await self.get_tenant(tenant_id)
        await self.session.delete(tenant)
        await self.session.flush()

    # ── Product CRUD ─────────────────────────────────────────────────────────

    async def list_products(
        self,
        page: int = 1,
        page_size: int = 20,
        module_name: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[Product], int]:
        """
        List products with pagination and optional filters.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            module_name: Optional module name filter.
            is_active: Optional active status filter.
            search: Optional search string for name or key.

        Returns:
            A tuple of (list of Product instances, total count).
        """
        query = select(Product)
        count_query = select(func.count(Product.id))

        if module_name:
            query = query.where(Product.module_name == module_name)
            count_query = count_query.where(Product.module_name == module_name)

        if is_active is not None:
            query = query.where(Product.is_active == is_active)
            count_query = count_query.where(Product.is_active == is_active)

        if search:
            pattern = f"%{search}%"
            query = query.where(
                Product.name.ilike(pattern) | Product.product_key.ilike(pattern)
            )
            count_query = count_query.where(
                Product.name.ilike(pattern) | Product.product_key.ilike(pattern)
            )

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.order_by(Product.sort_order, Product.created_at.desc()).offset(offset).limit(page_size)

        result = await self.session.execute(query)
        products = list(result.unique().scalars().all())

        return products, total

    async def get_product(self, product_id: str) -> Product:
        """
        Get a product by ID.

        Args:
            product_id: The UUID of the product.

        Returns:
            The Product instance.

        Raises:
            ProductNotFoundError: If the product is not found.
        """
        stmt = select(Product).where(Product.id == product_id)
        result = await self.session.execute(stmt)
        product = result.unique().scalar_one_or_none()
        if not product:
            msg = f"Product with id '{product_id}' not found"
            raise ProductNotFoundError(msg)
        return product

    async def create_product(self, data: ProductCreate) -> Product:
        """
        Create a new product.

        Args:
            data: Product creation data.

        Returns:
            The newly created Product instance.

        Raises:
            DuplicateProductKeyError: If the product key already exists.
        """
        # Check for duplicate key
        existing = await self.session.execute(
            select(Product).where(Product.product_key == data.product_key)
        )
        if existing.unique().scalar_one_or_none():
            msg = f"Product with key '{data.product_key}' already exists"
            raise DuplicateProductKeyError(msg)

        product = Product(
            module_name=data.module_name,
            product_key=data.product_key,
            name=data.name,
            description_i18n=data.description_i18n or {},
            price=data.price,
            billing_cycle=data.billing_cycle,
            currency=data.currency,
            is_active=data.is_active,
            metadata=data.metadata or {},
            sort_order=data.sort_order,
        )
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def update_product(self, product_id: str, data: ProductUpdate) -> Product:
        """
        Update a product.

        Args:
            product_id: The UUID of the product.
            data: The fields to update.

        Returns:
            The updated Product instance.

        Raises:
            ProductNotFoundError: If the product is not found.
        """
        product = await self.get_product(product_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)

        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def delete_product(self, product_id: str) -> None:
        """
        Soft-delete a product by setting it inactive.

        Args:
            product_id: The UUID of the product.

        Raises:
            ProductNotFoundError: If the product is not found.
        """
        product = await self.get_product(product_id)
        product.is_active = False
        await self.session.flush()

    async def hard_delete_product(self, product_id: str) -> None:
        """
        Permanently delete a product.

        Args:
            product_id: The UUID of the product.

        Raises:
            ProductNotFoundError: If the product is not found.
        """
        product = await self.get_product(product_id)
        await self.session.delete(product)
        await self.session.flush()

    # ── Abuse Report Management ──────────────────────────────────────────────

    async def list_abuse_reports(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        abuse_type: str | None = None,
    ) -> tuple[list[AbuseReport], int]:
        """
        List abuse reports with pagination and optional filters.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            status: Optional status filter.
            abuse_type: Optional abuse type filter.

        Returns:
            A tuple of (list of AbuseReport instances, total count).
        """
        query = select(AbuseReport)
        count_query = select(func.count(AbuseReport.id))

        if status:
            query = query.where(AbuseReport.status == status)
            count_query = count_query.where(AbuseReport.status == status)

        if abuse_type:
            query = query.where(AbuseReport.abuse_type == abuse_type)
            count_query = count_query.where(AbuseReport.abuse_type == abuse_type)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.order_by(AbuseReport.created_at.desc()).offset(offset).limit(page_size)

        result = await self.session.execute(query)
        reports = list(result.unique().scalars().all())

        return reports, total

    async def get_abuse_report(self, report_id: str) -> AbuseReport:
        """
        Get an abuse report by ID.

        Args:
            report_id: The UUID of the report.

        Returns:
            The AbuseReport instance.

        Raises:
            AbuseReportNotFoundError: If the report is not found.
        """
        stmt = select(AbuseReport).where(AbuseReport.id == report_id)
        result = await self.session.execute(stmt)
        report = result.unique().scalar_one_or_none()
        if not report:
            msg = f"Abuse report with id '{report_id}' not found"
            raise AbuseReportNotFoundError(msg)
        return report

    async def update_abuse_report(
        self,
        report_id: str,
        status: str,
        admin_notes: str | None = None,
        resolved_by: str | None = None,
    ) -> AbuseReport:
        """
        Update an abuse report status and notes.

        Args:
            report_id: The UUID of the report.
            status: The new status.
            admin_notes: Optional admin notes.
            resolved_by: Optional resolver identifier.

        Returns:
            The updated AbuseReport instance.

        Raises:
            AbuseReportNotFoundError: If the report is not found.
        """
        report = await self.get_abuse_report(report_id)
        report.status = status
        if admin_notes is not None:
            report.admin_notes = admin_notes
        if resolved_by is not None:
            report.resolved_by = resolved_by

        # Set resolved_at if status is resolved
        if status in (
            AbuseReportStatus.RESOLVED.value,
            AbuseReportStatus.DISMISSED.value,
        ):
            report.resolved_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(report)
        return report

    # ── User Management (Admin) ──────────────────────────────────────────────

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        role: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        tenant_id: str | None = None,
    ) -> tuple[list[User], int]:
        """
        List users with pagination and optional filters (admin view).

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            role: Optional role filter.
            is_active: Optional active status filter.
            search: Optional search string.
            tenant_id: Optional tenant ID filter.

        Returns:
            A tuple of (list of User instances, total count).
        """
        query = select(User)
        count_query = select(func.count(User.id))

        if role:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)

        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        if tenant_id:
            query = query.where(User.tenant_id == tenant_id)
            count_query = count_query.where(User.tenant_id == tenant_id)

        if search:
            pattern = f"%{search}%"
            query = query.where(
                User.email.ilike(pattern) | User.full_name.ilike(pattern)
            )
            count_query = count_query.where(
                User.email.ilike(pattern) | User.full_name.ilike(pattern)
            )

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)

        result = await self.session.execute(query)
        users = list(result.unique().scalars().all())

        return users, total

    # ── Service Management (Admin) ───────────────────────────────────────────

    async def list_services(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        module_name: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
    ) -> tuple[list[Service], int]:
        """
        List services with pagination and optional filters.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            status: Optional status filter.
            module_name: Optional module name filter.
            tenant_id: Optional tenant ID filter.
            user_id: Optional user ID filter.

        Returns:
            A tuple of (list of Service instances, total count).
        """
        query = select(Service)
        count_query = select(func.count(Service.id))

        if status:
            query = query.where(Service.status == status)
            count_query = count_query.where(Service.status == status)

        if module_name:
            query = query.where(Service.module_name == module_name)
            count_query = count_query.where(Service.module_name == module_name)

        if tenant_id:
            query = query.where(Service.tenant_id == tenant_id)
            count_query = count_query.where(Service.tenant_id == tenant_id)

        if user_id:
            query = query.where(Service.user_id == user_id)
            count_query = count_query.where(Service.user_id == user_id)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.order_by(Service.created_at.desc()).offset(offset).limit(page_size)

        result = await self.session.execute(query)
        services = list(result.unique().scalars().all())

        return services, total

    # ── License Key Generation ───────────────────────────────────────────────

    async def generate_license_key(self) -> str:
        """Generate a new cryptographically secure license key."""
        return generate_license_key()

    # ── Bulk Operations ──────────────────────────────────────────────────────

    async def bulk_activate_tenants(self, tenant_ids: list[str]) -> int:
        """
        Activate multiple tenants by IDs.

        Args:
            tenant_ids: List of tenant UUIDs.

        Returns:
            Number of activated tenants.
        """
        stmt = (
            select(Tenant)
            .where(Tenant.id.in_(tenant_ids))
            .where(Tenant.active == False)  # noqa: E712
        )
        result = await self.session.execute(stmt)
        tenants = list(result.unique().scalars().all())

        for tenant in tenants:
            tenant.active = True

        await self.session.flush()
        return len(tenants)

    async def bulk_deactivate_tenants(self, tenant_ids: list[str]) -> int:
        """
        Deactivate multiple tenants by IDs.

        Args:
            tenant_ids: List of tenant UUIDs.

        Returns:
            Number of deactivated tenants.
        """
        stmt = (
            select(Tenant)
            .where(Tenant.id.in_(tenant_ids))
            .where(Tenant.active == True)  # noqa: E712
        )
        result = await self.session.execute(stmt)
        tenants = list(result.unique().scalars().all())

        for tenant in tenants:
            tenant.active = False

        await self.session.flush()
        return len(tenants)


__all__ = [
    "AbuseReportNotFoundError",
    "AdminService",
    "DuplicateProductKeyError",
    "DuplicateTenantDomainError",
    "ProductNotFoundError",
    "TenantNotFoundError",
]