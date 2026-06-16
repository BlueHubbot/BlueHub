"""
Add VPN Servers Table
======================

Create the ``vpn_servers`` table for managing WireGuard server instances.

This migration is created after ``20260614_164420`` (vpn_accounts, vpn_sessions,
vpn_protocol_configs) because the ``vpn_servers`` FK reference was added to
``vpn_accounts`` in that migration but the table itself was not yet created.

Tables created:
    - vpn_servers : VPN server configurations and capacity tracking

Revision ID: 20260614_201944
Revises: 20260614_164420
Create Date: 2026-06-14 20:19:44.000000 (UTC+3:30)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260614_201944"
down_revision: str | None = "20260614_164420"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create the vpn_servers table.
    """
    op.create_table(
        "vpn_servers",
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False,
                  doc="Human-readable server name"),
        sa.Column("host", sa.String(length=255), nullable=False,
                  doc="Server hostname or IP for management SSH/API"),
        sa.Column("port", sa.Integer(), nullable=False,
                  server_default=sa.text("51820"),
                  doc="WireGuard listen port"),
        sa.Column("public_ip", sa.String(length=45), nullable=False,
                  doc="Server public IP address for client configuration"),
        sa.Column("private_key", sa.Text(), nullable=True,
                  doc="Server WireGuard private key (stored encrypted)"),
        sa.Column("public_key", sa.Text(), nullable=True,
                  doc="Server WireGuard public key"),
        sa.Column("endpoint", sa.String(length=255), nullable=False,
                  doc="Server endpoint for client config (IP:Port or domain:Port)"),
        sa.Column("country", sa.String(length=2), nullable=False,
                  server_default=sa.text("'US'"),
                  doc="ISO 3166-1 alpha-2 country code"),
        sa.Column("city", sa.String(length=100), nullable=True,
                  doc="Server city location"),
        sa.Column("provider", sa.String(length=100), nullable=True,
                  doc="Server hosting provider name"),
        sa.Column("bandwidth_limit_mbps", sa.Integer(), nullable=True,
                  doc="Bandwidth limit in Mbps for this server"),
        sa.Column("max_clients", sa.Integer(), nullable=False,
                  server_default=sa.text("100"),
                  doc="Maximum number of client peers this server can host"),
        sa.Column("current_clients", sa.Integer(), nullable=False,
                  server_default=sa.text("0"),
                  doc="Current number of active client peers"),
        sa.Column("is_active", sa.Boolean(), nullable=False,
                  server_default=sa.text("true"),
                  doc="Whether this server is accepting new clients"),
        sa.Column("notes", sa.Text(), nullable=True,
                  doc="Admin notes"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # Create indexes for common query patterns
    op.create_index("ix_vpn_servers_country", "vpn_servers", ["country"])
    op.create_index("ix_vpn_servers_is_active_country", "vpn_servers",
                    ["is_active", "country"])
    op.create_index("ix_vpn_servers_is_active_current_clients", "vpn_servers",
                    ["is_active", "current_clients"])


def downgrade() -> None:
    """
    Drop the vpn_servers table.
    """
    # Drop indexes
    op.drop_index("ix_vpn_servers_is_active_current_clients", table_name="vpn_servers")
    op.drop_index("ix_vpn_servers_is_active_country", table_name="vpn_servers")
    op.drop_index("ix_vpn_servers_country", table_name="vpn_servers")

    # Drop table
    op.drop_table("vpn_servers")