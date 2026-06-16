"""
BlueHub Billing Tables
======================

Add billing-related tables: invoices and transactions.

Tables created:
    - invoices       : Billing invoices for services and wallet top-ups
    - transactions   : Financial transaction audit trail for wallet operations

Revision ID: 20260614_030920
Revises: 20260613_235959
Create Date: 2026-06-14 03:09:20.000000 (UTC)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260614_030920"
down_revision: str | None = "20260613_235959"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create invoices and transactions tables.
    """
    # -----------------------------------------------------------------------
    # 1. Create invoices table
    # -----------------------------------------------------------------------
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(), nullable=False, index=True),
        sa.Column("service_id", postgresql.UUID(), nullable=True, index=True),
        sa.Column("invoice_number", sa.String(length=50), nullable=False, unique=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False,
                  server_default=sa.text("'pending'"), index=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("line_items", postgresql.JSONB, nullable=True,
                  doc="JSONB array of line items (description, amount, quantity)"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_invoices_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_invoices_service_id_services",
        ),
    )

    # -----------------------------------------------------------------------
    # 2. Create transactions table
    # -----------------------------------------------------------------------
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(), nullable=False, index=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("transaction_type", sa.String(length=30), nullable=False,
                  index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reference_id", sa.String(length=255), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_transactions_user_id_users",
        ),
    )

    # -----------------------------------------------------------------------
    # 3. Create indexes for common query patterns
    # -----------------------------------------------------------------------
    op.create_index("ix_invoices_user_status", "invoices", ["user_id", "status"])
    op.create_index("ix_transactions_user_type", "transactions",
                    ["user_id", "transaction_type"])


def downgrade() -> None:
    """
    Drop invoices and transactions tables.
    """
    # Drop indexes first
    op.drop_index("ix_transactions_user_type", table_name="transactions")
    op.drop_index("ix_invoices_user_status", table_name="invoices")

    # Drop tables
    op.drop_table("transactions")
    op.drop_table("invoices")
