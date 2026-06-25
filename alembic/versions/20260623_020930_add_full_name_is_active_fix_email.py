"""
Add full_name, is_active columns to users; fix email nullable
=============================================================

Adds missing columns to users table to match the current ORM model:
    - full_name : User's full display name (nullable)
    - is_active : Whether the user account is active (default: true)

Also alters email column from nullable=True to nullable=False
to match the current model definition.

Revision ID: 20260623_020930
Revises: 20260620_021230
Create Date: 2026-06-23 02:09:30.000000 (UTC)
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "20260623_020930"
down_revision: str | None = "20260620_021230"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add full_name, is_active columns; fix email nullable."""

    # 1. Add full_name column (nullable)
    op.add_column(
        "users",
        sa.Column("full_name", sa.String(length=255), nullable=True,
                  doc="User's full display name"),
    )

    # 2. Add is_active column (non-nullable, default true)
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False,
                  server_default=sa.text("true"),
                  doc="Whether the user account is active"),
    )

    # 3. Fix email: change from nullable=True to nullable=False
    # First, ensure there are no NULL email values in production
    op.execute(
        "UPDATE users SET email = 'migrated-' || id || '@bluehub.local' "
        "WHERE email IS NULL"
    )
    # Then alter the column to be NOT NULL
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=255),
        nullable=False,
    )

    # 4. Create index on is_active for admin queries
    op.create_index("ix_users_is_active", "users", ["is_active"])


def downgrade() -> None:
    """Reverse the changes: remove columns, revert email to nullable."""

    # 1. Revert email to nullable
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=255),
        nullable=True,
    )

    # 2. Remove is_active column
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_column("users", "is_active")

    # 3. Remove full_name column
    op.drop_column("users", "full_name")
