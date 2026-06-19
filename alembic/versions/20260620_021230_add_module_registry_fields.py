"""
Add bot_keyboard, admin_menu, default_config to module_registry.
Revision ID: 20260620_021230
Revises: 20260615_201200_vps_tables
Create Date: 2026-06-20 02:12:30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision: str = "20260620_021230"
down_revision: str | None = "20260615_201200_vps_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add bot_keyboard, admin_menu, default_config JSONB columns."""
    op.add_column(
        "module_registry",
        sa.Column("bot_keyboard", JSONB(), nullable=True, default=None),
    )
    op.add_column(
        "module_registry",
        sa.Column("admin_menu", JSONB(), nullable=True, default=None),
    )
    op.add_column(
        "module_registry",
        sa.Column("default_config", JSONB(), nullable=True, default=None),
    )


def downgrade() -> None:
    """Remove the added columns."""
    op.drop_column("module_registry", "default_config")
    op.drop_column("module_registry", "admin_menu")
    op.drop_column("module_registry", "bot_keyboard")