"""
BlueHub Initial Schema
========================

Create initial database schema for BlueHub platform.
Contains all core tables for multi-tenant operation.

Tables created:
    - tenants          : Multi-tenant organizations/brands
    - users            : Platform users with auth fields
    - products         : Product catalog with i18n support
    - tenant_product_pricing : Tenant-specific pricing overrides
    - services         : Core service model for all product types
    - reseller_commissions    : Reseller commission tracking
    - module_registry   : Plug-and-play module registration
    - audit_logs        : Audit trail for security events

Revision ID: 20260613_235959
Revises: None
Create Date: 2026-06-13 23:59:59.000000 (UTC)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260613_235959"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create the initial schema with 8 tables.
    """
    # -----------------------------------------------------------------------
    # 1. Enable UUID extension (idempotent)
    # -----------------------------------------------------------------------
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # -----------------------------------------------------------------------
    # 2. ENUM types will be auto-created by SQLAlchemy via sa.Enum
    #    (checkfirst=True is the default, uses CREATE TYPE IF NOT EXISTS)
    # -----------------------------------------------------------------------

    # -----------------------------------------------------------------------
    # 3. Create tables
    # -----------------------------------------------------------------------

    # -- tenants -----------------------------------------------------------------
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column("logo_url", sa.String(length=512), nullable=True),
        sa.Column("branding_config", postgresql.JSONB, nullable=True,
                  doc="JSONB branding configuration (colors, fonts, theme)"),
        sa.Column("telegram_bot_token", sa.String(length=255), nullable=True),
        sa.Column("license_key", sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # -- users -------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(), nullable=True, index=True),
        sa.Column("paymenter_user_id", sa.BigInteger(), nullable=True, unique=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=True, unique=True),
        sa.Column("email", sa.String(length=255), nullable=True, unique=True, index=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("role", sa.Enum("superadmin", "admin", "reseller", "user",
                                  name="userrole", create_type=True),
                  nullable=False, server_default="user"),
        sa.Column("language_code", sa.String(length=10), nullable=False,
                  server_default="en"),
        sa.Column("two_fa_enabled", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("totp_secret", sa.String(length=64), nullable=True),
        sa.Column("wallet_balance", sa.Float(), nullable=False,
                  server_default=sa.text("0.0")),
        sa.Column("migrated", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("migrated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_users_tenant_id_tenants",
        ),
    )

    # -- products ----------------------------------------------------------------
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        sa.Column("module_name", sa.String(length=50), nullable=False, index=True),
        sa.Column("product_key", sa.String(length=255), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description_i18n", postgresql.JSONB, nullable=True),
        sa.Column("base_price", sa.Float(), nullable=False),
        sa.Column("billing_cycle", sa.Enum("monthly", "quarterly", "semi_annually",
                                           "annually", "biennially", "triennially",
                                           name="billingcycle", create_type=True),
                  nullable=False, server_default="monthly"),
        sa.Column("billing_cycle_days", sa.Integer(), nullable=False),
        sa.Column("specs", postgresql.JSONB, nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # -- services ----------------------------------------------------------------
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(), nullable=False, index=True),
        sa.Column("tenant_id", postgresql.UUID(), nullable=False, index=True),
        sa.Column("product_id", postgresql.UUID(), nullable=False, index=True),
        sa.Column("module_name", sa.String(length=50), nullable=False),
        sa.Column("status", sa.Enum("pending", "active", "suspended",
                                    "expired", "cancelled", "terminated",
                                    name="servicestatus", create_type=True),
                  nullable=False, server_default="pending", index=True),
        sa.Column("price_paid", sa.Float(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("provisioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspension_reason", sa.Text(), nullable=True),
        sa.Column("service_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_services_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_services_tenant_id_tenants",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_services_product_id_products",
        ),
    )

    # -- tenant_product_pricing --------------------------------------------------
    op.create_table(
        "tenant_product_pricing",
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(), nullable=False, index=True),
        sa.Column("product_id", postgresql.UUID(), nullable=False, index=True),
        sa.Column("price_override", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_tenant_product_pricing_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_tenant_product_pricing_product_id_products",
            ondelete="CASCADE",
        ),
    )

    # -- reseller_commissions ----------------------------------------------------
    op.create_table(
        "reseller_commissions",
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        sa.Column("reseller_id", postgresql.UUID(), nullable=False, index=True),
        sa.Column("service_id", postgresql.UUID(), nullable=False),
        sa.Column("commission_rate", sa.Float(), nullable=False),
        sa.Column("commission_amount", sa.Float(), nullable=False),
        sa.Column("status", sa.Enum("pending", "paid", "cancelled",
                                    name="commissionstatus", create_type=True),
                  nullable=False, server_default="pending"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["reseller_id"],
            ["users.id"],
            name="fk_reseller_commissions_reseller_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_reseller_commissions_service_id_services",
            ondelete="CASCADE",
        ),
    )

    # -- module_registry ---------------------------------------------------------
    op.create_table(
        "module_registry",
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        sa.Column("module_name", sa.String(length=50), nullable=False, unique=True, index=True),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=20), nullable=False,
                  server_default="1.0.0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("config_schema", postgresql.JSONB, nullable=True),
        sa.Column("flags", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # -- audit_logs --------------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(), nullable=True, index=True),
        sa.Column("tenant_id", postgresql.UUID(), nullable=True, index=True),
        sa.Column("action", sa.Enum("create", "read", "update", "delete",
                                    "login", "logout", "suspend", "unsuspend",
                                    "terminate", "payment", "refund",
                                    name="auditaction", create_type=True),
                  nullable=False, index=True),
        sa.Column("entity_type", sa.String(length=100), nullable=False, index=True),
        sa.Column("entity_id", sa.String(length=255), nullable=True),
        sa.Column("changes", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("actor_role", sa.String(length=50), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_audit_logs_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_audit_logs_tenant_id_tenants",
        ),
    )

    # -----------------------------------------------------------------------
    # 4. Create composite indexes for common query patterns
    # -----------------------------------------------------------------------
    op.create_index("ix_users_tenant_role", "users", ["tenant_id", "role"])
    op.create_index("ix_services_user_status", "services", ["user_id", "status"])
    op.create_index("ix_services_tenant_status", "services", ["tenant_id", "status"])
    op.create_index("ix_services_expiry", "services", ["expires_at", "status"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_reseller_commissions_status", "reseller_commissions",
                    ["reseller_id", "status"])

    # -----------------------------------------------------------------------
    # 5. Create partial unique indexes for business rules
    # -----------------------------------------------------------------------
    op.create_index("ix_products_module_active", "products",
                    ["module_name", "active"],
                    postgresql_where=sa.text("active = true"))
    op.create_index("ix_tenant_pricing_unique", "tenant_product_pricing",
                    ["tenant_id", "product_id"],
                    unique=True,
                    postgresql_where=sa.text("true"))


def downgrade() -> None:
    """
    Drop all tables and custom ENUM types to revert to empty state.
    Tables are dropped in reverse dependency order (children before parents).
    """
    # Drop tables in reverse creation order (children before parents)
    op.drop_table("audit_logs")
    op.drop_table("module_registry")
    op.drop_table("reseller_commissions")
    op.drop_table("tenant_product_pricing")
    op.drop_table("services")
    op.drop_table("products")
    op.drop_table("users")
    op.drop_table("tenants")

    # Drop custom ENUM types (must be done after all dependent tables are dropped)
    op.execute("DROP TYPE IF EXISTS auditaction")
    op.execute("DROP TYPE IF EXISTS commissionstatus")
    op.execute("DROP TYPE IF EXISTS billingcycle")
    op.execute("DROP TYPE IF EXISTS servicestatus")
    op.execute("DROP TYPE IF EXISTS userrole")
