"""
BlueHub Billing Service
========================
Service layer for billing operations including wallet management,
invoice processing, transaction recording, product catalog,
tenant pricing, and commission tracking.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.billing.schemas import (
    CreateInvoiceRequest,
    CreateProductRequest,
    MarkCommissionPaidRequest,
    SetTenantPricingRequest,
    UpdateProductRequest,
    WalletDeductRequest,
    WalletTopUpRequest,
)
from shared.models.enums import CommissionStatus
from shared.models.invoice import Invoice
from shared.models.product import Product, ResellerCommission, TenantProductPricing
from shared.models.transaction import Transaction
from shared.models.user import User

# ── Exception Classes ──────────────────────────────────────────────────────


class BillingError(Exception):
    """Base exception for billing errors."""


class InsufficientBalanceError(BillingError):
    """Raised when wallet balance is insufficient for a deduction."""


class UserNotFoundError(BillingError):
    """Raised when the specified user is not found."""


class InvoiceNotFoundError(BillingError):
    """Raised when an invoice is not found."""


class TransactionNotFoundError(BillingError):
    """Raised when a transaction is not found."""


class ProductNotFoundError(BillingError):
    """Raised when a product is not found."""


class CommissionNotFoundError(BillingError):
    """Raised when a commission is not found."""


class PricingNotFoundError(BillingError):
    """Raised when tenant pricing is not found."""


class DuplicateInvoiceNumberError(BillingError):
    """Raised when attempting to create an invoice with a duplicate number."""


# ── BillingService ──────────────────────────────────────────────────────────


class BillingService:
    """Service for all billing operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Helper Methods ────────────────────────────────────────────────────

    async def _get_user(self, user_id: str) -> User:
        """Get a user by ID or raise UserNotFoundError."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.unique().scalar_one_or_none()
        if not user:
            msg = f"User with id '{user_id}' not found"
            raise UserNotFoundError(msg)
        return user

    async def _generate_invoice_number(self) -> str:
        """Generate a unique invoice number."""
        timestamp = int(datetime.now(UTC).timestamp())
        # Use count for ordering to ensure uniqueness
        stmt = select(func.count(Invoice.id))
        result = await self.session.execute(stmt)
        count = result.scalar() or 0
        return f"INV-{timestamp}-{count + 1}"

    # ── Wallet Operations ─────────────────────────────────────────────────

    async def get_wallet_balance(self, user_id: str) -> dict:
        """
        Get the wallet balance for a user.

        Args:
            user_id: The UUID of the user.

        Returns:
            Dict with user_id, wallet_balance, and currency.

        Raises:
            UserNotFoundError: If the user is not found.
        """
        user = await self._get_user(user_id)
        return {
            "user_id": str(user.id),
            "wallet_balance": user.wallet_balance or 0.0,
            "currency": "USD",
        }

    async def top_up_wallet(
        self, user_id: str, request: WalletTopUpRequest
    ) -> dict:
        """
        Add funds to a user's wallet.

        Args:
            user_id: The UUID of the user.
            request: Top-up details including amount and optional description.

        Returns:
            The updated wallet balance.

        Raises:
            UserNotFoundError: If the user is not found.
        """
        user = await self._get_user(user_id)
        user.wallet_balance = (user.wallet_balance or 0.0) + request.amount

        # Record the transaction
        transaction = Transaction(
            user_id=user.id,
            amount=request.amount,
            transaction_type="top_up",
            description=request.description or "Wallet top-up",
        )
        self.session.add(transaction)

        await self.session.flush()
        await self.session.refresh(user)

        return {
            "user_id": str(user.id),
            "wallet_balance": user.wallet_balance,
            "currency": "USD",
        }

    async def deduct_wallet(
        self, user_id: str, request: WalletDeductRequest
    ) -> dict:
        """
        Deduct funds from a user's wallet.

        Args:
            user_id: The UUID of the user.
            request: Deduction details including amount and optional description.

        Returns:
            The updated wallet balance.

        Raises:
            UserNotFoundError: If the user is not found.
            InsufficientBalanceError: If the wallet balance is insufficient.
        """
        user = await self._get_user(user_id)
        current_balance = user.wallet_balance or 0.0

        if current_balance < request.amount:
            msg = (
                f"Insufficient balance. "
                f"Available: {current_balance}, Required: {request.amount}"
            )
            raise InsufficientBalanceError(
                msg
            )

        user.wallet_balance = current_balance - request.amount

        # Record the transaction (negative amount for deductions)
        transaction = Transaction(
            user_id=user.id,
            amount=-request.amount,
            transaction_type="deduction",
            description=request.description or "Wallet deduction",
        )
        self.session.add(transaction)

        await self.session.flush()
        await self.session.refresh(user)

        return {
            "user_id": str(user.id),
            "wallet_balance": user.wallet_balance,
            "currency": "USD",
        }

    # ── Transaction Operations ────────────────────────────────────────────

    async def create_transaction(
        self,
        user_id: str,
        amount: float,
        transaction_type: str,
        description: str | None = None,
        reference_id: str | None = None,
    ) -> Transaction:
        """
        Record a financial transaction.

        Args:
            user_id: The UUID of the user.
            amount: The transaction amount (positive for credits, negative for debits).
            transaction_type: Type of transaction (top_up, deduction, payment, etc.).
            description: Optional human-readable description.
            reference_id: Optional reference ID (invoice, commission, etc.).

        Returns:
            The created Transaction instance.
        """
        transaction = Transaction(
            user_id=user_id,
            amount=round(amount, 2),
            transaction_type=transaction_type,
            description=description,
            reference_id=reference_id,
        )
        self.session.add(transaction)
        await self.session.flush()
        await self.session.refresh(transaction)
        return transaction

    async def list_transactions(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        transaction_type: str | None = None,
    ) -> tuple[list[Transaction], int]:
        """
        List transactions for a user with pagination.

        Args:
            user_id: The UUID of the user.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            transaction_type: Optional filter by transaction type.

        Returns:
            A tuple of (list of Transaction instances, total count).
        """
        query = select(Transaction).where(Transaction.user_id == user_id)
        count_query = select(func.count(Transaction.id)).where(
            Transaction.user_id == user_id
        )

        if transaction_type:
            query = query.where(Transaction.transaction_type == transaction_type)
            count_query = count_query.where(
                Transaction.transaction_type == transaction_type
            )

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        query = (
            query.order_by(Transaction.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.session.execute(query)
        transactions = list(result.unique().scalars().all())

        return transactions, total

    # ── Invoice Operations ────────────────────────────────────────────────

    async def create_invoice(self, request: CreateInvoiceRequest) -> Invoice:
        """
        Create a new invoice.

        Args:
            request: Invoice creation details.

        Returns:
            The created Invoice instance.

        Raises:
            UserNotFoundError: If the user is not found.
            DuplicateInvoiceNumberError: If invoice number generation fails.
        """
        # Verify user exists
        await self._get_user(request.user_id)

        invoice_number = await self._generate_invoice_number()

        invoice = Invoice(
            user_id=request.user_id,
            service_id=request.service_id,
            invoice_number=invoice_number,
            amount=round(request.amount, 2),
            status="pending",
            due_date=request.due_date,
            description=request.description,
            line_items=request.line_items or [],
        )
        self.session.add(invoice)
        await self.session.flush()
        await self.session.refresh(invoice)
        return invoice

    async def get_invoice(self, invoice_id: str) -> Invoice:
        """
        Get an invoice by ID.

        Args:
            invoice_id: The UUID of the invoice.

        Returns:
            The Invoice instance.

        Raises:
            InvoiceNotFoundError: If the invoice is not found.
        """
        stmt = select(Invoice).where(Invoice.id == invoice_id)
        result = await self.session.execute(stmt)
        invoice = result.unique().scalar_one_or_none()
        if not invoice:
            msg = f"Invoice with id '{invoice_id}' not found"
            raise InvoiceNotFoundError(
                msg
            )
        return invoice

    async def list_invoices(
        self,
        user_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Invoice], int]:
        """
        List invoices with optional filters and pagination.

        Args:
            user_id: Optional filter by user ID.
            status: Optional filter by invoice status.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            A tuple of (list of Invoice instances, total count).
        """
        query = select(Invoice)
        count_query = select(func.count(Invoice.id))

        if user_id:
            query = query.where(Invoice.user_id == user_id)
            count_query = count_query.where(Invoice.user_id == user_id)

        if status:
            query = query.where(Invoice.status == status)
            count_query = count_query.where(Invoice.status == status)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        query = (
            query.order_by(Invoice.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.session.execute(query)
        invoices = list(result.unique().scalars().all())

        return invoices, total

    async def mark_invoice_paid(
        self, invoice_id: str, paid_at: datetime | None = None
    ) -> Invoice:
        """
        Mark an invoice as paid.

        Args:
            invoice_id: The UUID of the invoice.
            paid_at: Optional timestamp of payment (defaults to now).

        Returns:
            The updated Invoice instance.

        Raises:
            InvoiceNotFoundError: If the invoice is not found.
        """
        invoice = await self.get_invoice(invoice_id)
        invoice.status = "paid"
        invoice.paid_at = paid_at or datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(invoice)
        return invoice

    async def cancel_invoice(self, invoice_id: str) -> Invoice:
        """
        Cancel an invoice.

        Args:
            invoice_id: The UUID of the invoice.

        Returns:
            The updated Invoice instance.

        Raises:
            InvoiceNotFoundError: If the invoice is not found.
        """
        invoice = await self.get_invoice(invoice_id)
        invoice.status = "cancelled"

        await self.session.flush()
        await self.session.refresh(invoice)
        return invoice

    # ── Product Catalog Operations ────────────────────────────────────────

    async def create_product(self, request: CreateProductRequest) -> Product:
        """
        Create a new product in the catalog.

        Args:
            request: Product creation details.

        Returns:
            The created Product instance.
        """
        product = Product(
            module_name=request.module_name,
            product_key=request.product_key,
            name=request.name,
            description_i18n=request.description_i18n or {},
            base_price=round(request.base_price, 2),
            billing_cycle=request.billing_cycle,
            billing_cycle_days=request.billing_cycle_days,
            specs=request.specs or {},
            order=request.order,
            active=request.active,
        )
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product)
        return product

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
            raise ProductNotFoundError(
                msg
            )
        return product

    async def list_products(
        self,
        module_name: str | None = None,
        active_only: bool = True,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Product], int]:
        """
        List products with optional filters.

        Args:
            module_name: Optional filter by module name.
            active_only: If True, only return active products.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            A tuple of (list of Product instances, total count).
        """
        query = select(Product)
        count_query = select(func.count(Product.id))

        if module_name:
            query = query.where(Product.module_name == module_name)
            count_query = count_query.where(
                Product.module_name == module_name
            )

        if active_only:
            query = query.where(Product.active)
            count_query = count_query.where(Product.active)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        query = (
            query.order_by(Product.order.asc(), Product.name.asc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.session.execute(query)
        products = list(result.unique().scalars().all())

        return products, total

    async def update_product(
        self, product_id: str, request: UpdateProductRequest
    ) -> Product:
        """
        Update an existing product.

        Args:
            product_id: The UUID of the product to update.
            request: The fields to update.

        Returns:
            The updated Product instance.

        Raises:
            ProductNotFoundError: If the product is not found.
        """
        product = await self.get_product(product_id)
        update_data = request.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == "base_price" and value is not None:
                value = round(value, 2)
            setattr(product, field, value)

        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def delete_product(self, product_id: str) -> None:
        """
        Deactivate a product (soft delete by setting active=False).

        Args:
            product_id: The UUID of the product to deactivate.

        Raises:
            ProductNotFoundError: If the product is not found.
        """
        product = await self.get_product(product_id)
        product.active = False
        await self.session.flush()

    # ── Tenant Pricing Operations ─────────────────────────────────────────

    async def set_tenant_pricing(
        self, tenant_id: str, request: SetTenantPricingRequest
    ) -> TenantProductPricing:
        """
        Set or update tenant-specific pricing for a product.

        Args:
            tenant_id: The UUID of the tenant.
            request: Pricing details.

        Returns:
            The TenantProductPricing instance.

        Raises:
            ProductNotFoundError: If the product is not found.
        """
        # Verify product exists
        await self.get_product(request.product_id)

        # Check if pricing already exists for this tenant+product
        stmt = select(TenantProductPricing).where(
            TenantProductPricing.tenant_id == tenant_id,
            TenantProductPricing.product_id == request.product_id,
        )
        result = await self.session.execute(stmt)
        pricing = result.unique().scalar_one_or_none()

        if pricing:
            # Update existing pricing
            pricing.price_override = round(request.price_override, 2)
        else:
            # Create new pricing
            pricing = TenantProductPricing(
                tenant_id=tenant_id,
                product_id=request.product_id,
                price_override=round(request.price_override, 2),
            )
            self.session.add(pricing)

        await self.session.flush()
        await self.session.refresh(pricing)
        return pricing

    async def get_tenant_pricing(
        self, tenant_id: str, product_id: str
    ) -> TenantProductPricing:
        """
        Get tenant-specific pricing for a product.

        Args:
            tenant_id: The UUID of the tenant.
            product_id: The UUID of the product.

        Returns:
            The TenantProductPricing instance.

        Raises:
            PricingNotFoundError: If pricing is not found.
        """
        stmt = select(TenantProductPricing).where(
            TenantProductPricing.tenant_id == tenant_id,
            TenantProductPricing.product_id == product_id,
        )
        result = await self.session.execute(stmt)
        pricing = result.unique().scalar_one_or_none()
        if not pricing:
            msg = (
                f"Pricing not found for tenant '{tenant_id}' "
                f"and product '{product_id}'"
            )
            raise PricingNotFoundError(
                msg
            )
        return pricing

    async def list_tenant_pricing(
        self, tenant_id: str
    ) -> list[TenantProductPricing]:
        """
        List all custom pricing for a tenant.

        Args:
            tenant_id: The UUID of the tenant.

        Returns:
            A list of TenantProductPricing instances.
        """
        stmt = select(TenantProductPricing).where(
            TenantProductPricing.tenant_id == tenant_id
        )
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())

    async def delete_tenant_pricing(
        self, tenant_id: str, product_id: str
    ) -> None:
        """
        Remove tenant-specific pricing for a product.

        Args:
            tenant_id: The UUID of the tenant.
            product_id: The UUID of the product.

        Raises:
            PricingNotFoundError: If pricing is not found.
        """
        pricing = await self.get_tenant_pricing(tenant_id, product_id)
        await self.session.delete(pricing)
        await self.session.flush()

    # ── Commission Operations ─────────────────────────────────────────────

    async def create_commission(
        self,
        reseller_id: str,
        service_id: str,
        commission_rate: float,
        commission_amount: float,
    ) -> ResellerCommission:
        """
        Create a commission record for a reseller.

        Args:
            reseller_id: The UUID of the reseller.
            service_id: The UUID of the purchased service.
            commission_rate: The commission rate as a decimal (e.g. 0.10).
            commission_amount: The calculated commission amount.

        Returns:
            The created ResellerCommission instance.
        """
        commission = ResellerCommission(
            reseller_id=reseller_id,
            service_id=service_id,
            commission_rate=commission_rate,
            commission_amount=round(commission_amount, 2),
            status=CommissionStatus.PENDING,
        )
        self.session.add(commission)
        await self.session.flush()
        await self.session.refresh(commission)
        return commission

    async def list_commissions(
        self,
        reseller_id: str | None = None,
        status: CommissionStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ResellerCommission], int]:
        """
        List commissions with optional filters.

        Args:
            reseller_id: Optional filter by reseller ID.
            status: Optional filter by commission status.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            A tuple of (list of ResellerCommission instances, total count).
        """
        query = select(ResellerCommission)
        count_query = select(func.count(ResellerCommission.id))

        if reseller_id:
            query = query.where(
                ResellerCommission.reseller_id == reseller_id
            )
            count_query = count_query.where(
                ResellerCommission.reseller_id == reseller_id
            )

        if status:
            query = query.where(ResellerCommission.status == status)
            count_query = count_query.where(
                ResellerCommission.status == status
            )

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        query = (
            query.order_by(ResellerCommission.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.session.execute(query)
        commissions = list(result.unique().scalars().all())

        return commissions, total

    async def mark_commissions_paid(
        self, request: MarkCommissionPaidRequest
    ) -> list[ResellerCommission]:
        """
        Mark commissions as paid.

        Args:
            request: Contains list of commission IDs to mark as paid.

        Returns:
            List of updated ResellerCommission instances.

        Raises:
            CommissionNotFoundError: If any commission is not found.
        """
        now = datetime.now(UTC)
        updated_commissions = []

        for commission_id in request.commission_ids:
            stmt = select(ResellerCommission).where(
                ResellerCommission.id == commission_id
            )
            result = await self.session.execute(stmt)
            commission = result.unique().scalar_one_or_none()

            if not commission:
                msg = f"Commission with id '{commission_id}' not found"
                raise CommissionNotFoundError(
                    msg
                )

            commission.status = CommissionStatus.PAID
            commission.paid_at = now
            updated_commissions.append(commission)

        await self.session.flush()

        # Refresh all updated commissions
        for commission in updated_commissions:
            await self.session.refresh(commission)

        return updated_commissions

    # ── Billing Summary & Reports ─────────────────────────────────────────

    async def get_billing_summary(self, user_id: str) -> dict:
        """
        Get a billing summary for a user.

        Args:
            user_id: The UUID of the user.

        Returns:
            Dict with wallet balance, invoice stats, total spent, and commissions.

        Raises:
            UserNotFoundError: If the user is not found.
        """
        user = await self._get_user(user_id)

        # Invoice statistics
        total_stmt = select(func.count(Invoice.id)).where(
            Invoice.user_id == user_id
        )
        paid_stmt = select(func.count(Invoice.id)).where(
            Invoice.user_id == user_id, Invoice.status == "paid"
        )
        pending_stmt = select(func.count(Invoice.id)).where(
            Invoice.user_id == user_id, Invoice.status == "pending"
        )
        overdue_stmt = select(func.count(Invoice.id)).where(
            Invoice.user_id == user_id, Invoice.status == "overdue"
        )
        spent_stmt = select(func.coalesce(func.sum(Invoice.amount), 0)).where(
            Invoice.user_id == user_id, Invoice.status == "paid"
        )

        total_result = await self.session.execute(total_stmt)
        paid_result = await self.session.execute(paid_stmt)
        pending_result = await self.session.execute(pending_stmt)
        overdue_result = await self.session.execute(overdue_stmt)
        spent_result = await self.session.execute(spent_stmt)

        total_invoices = total_result.scalar() or 0
        paid_invoices = paid_result.scalar() or 0
        pending_invoices = pending_result.scalar() or 0
        overdue_invoices = overdue_result.scalar() or 0
        total_spent = spent_result.scalar() or 0.0

        result = {
            "wallet_balance": user.wallet_balance or 0.0,
            "total_invoices": total_invoices,
            "paid_invoices": paid_invoices,
            "pending_invoices": pending_invoices,
            "overdue_invoices": overdue_invoices,
            "total_spent": total_spent,
        }

        # Commission stats (if user is reseller)
        if user.is_reseller:
            pending_comm_stmt = select(
                func.coalesce(func.sum(ResellerCommission.commission_amount), 0)
            ).where(
                ResellerCommission.reseller_id == user_id,
                ResellerCommission.status == CommissionStatus.PENDING,
            )
            total_comm_stmt = select(
                func.coalesce(func.sum(ResellerCommission.commission_amount), 0)
            ).where(
                ResellerCommission.reseller_id == user_id,
            )

            pending_comm_result = await self.session.execute(pending_comm_stmt)
            total_comm_result = await self.session.execute(total_comm_stmt)

            result["pending_commissions"] = pending_comm_result.scalar() or 0.0
            result["total_commissions"] = total_comm_result.scalar() or 0.0

        return result

    async def get_revenue_report(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        """
        Get a revenue report for a date range.

        Args:
            period_start: Start of the reporting period.
            period_end: End of the reporting period.

        Returns:
            Dict with revenue totals, invoice count, top-up count.
        """
        # Total revenue from paid invoices
        revenue_stmt = select(
            func.coalesce(func.sum(Invoice.amount), 0)
        ).where(
            Invoice.status == "paid",
            Invoice.paid_at >= period_start,
            Invoice.paid_at <= period_end,
        )

        # Total commissions paid
        commissions_stmt = select(
            func.coalesce(func.sum(ResellerCommission.commission_amount), 0)
        ).where(
            ResellerCommission.status == CommissionStatus.PAID,
            ResellerCommission.paid_at >= period_start,
            ResellerCommission.paid_at <= period_end,
        )

        # Invoice count
        invoice_count_stmt = select(func.count(Invoice.id)).where(
            Invoice.status == "paid",
            Invoice.paid_at >= period_start,
            Invoice.paid_at <= period_end,
        )

        # Top-up count
        top_up_count_stmt = select(func.count(Transaction.id)).where(
            Transaction.transaction_type == "top_up",
            Transaction.created_at >= period_start,
            Transaction.created_at <= period_end,
        )

        revenue_result = await self.session.execute(revenue_stmt)
        commissions_result = await self.session.execute(commissions_stmt)
        invoice_count_result = await self.session.execute(invoice_count_stmt)
        top_up_count_result = await self.session.execute(top_up_count_stmt)

        total_revenue = revenue_result.scalar() or 0.0
        total_commissions = commissions_result.scalar() or 0.0
        invoice_count = invoice_count_result.scalar() or 0
        top_up_count = top_up_count_result.scalar() or 0

        return {
            "total_revenue": total_revenue,
            "total_commissions": total_commissions,
            "net_revenue": total_revenue - total_commissions,
            "invoice_count": invoice_count,
            "top_up_count": top_up_count,
            "period_start": period_start,
            "period_end": period_end,
        }


__all__ = [
    "BillingError",
    "BillingService",
    "CommissionNotFoundError",
    "DuplicateInvoiceNumberError",
    "InsufficientBalanceError",
    "InvoiceNotFoundError",
    "PricingNotFoundError",
    "ProductNotFoundError",
    "TransactionNotFoundError",
    "UserNotFoundError",
]
