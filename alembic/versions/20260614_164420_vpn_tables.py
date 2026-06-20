"""
BlueHub VPN Module Tables
==========================

Add VPN-related tables: vpn_accounts, vpn_sessions, vpn_protocol_configs.

Tables created:
    - vpn_accounts          : VPN account credentials and protocol config per service
    - vpn_protocol_configs  : Protocol-specific configuration key-value pairs
    - vpn_sessions          : VPN connection/disconnection session logs

Revision ID: 20260614_164420
Revises: 20260614_030920
Create Date: 2026-06-14 16:44:20.000000 (UTC+3:30)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260614_164420"
down_revision: str | None = "20260614_030920"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create vpn_accounts, vpn_protocol_configs, and vpn_sessions tables.
    """
    # -----------------------------------------------------------------------
    # 1. Create vpn_accounts table
    # -----------------------------------------------------------------------
    op.create_table(
        "vpn_accounts",
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        sa.Column("service_id", postgresql.UUID(), nullable=False, unique=True, index=True),
        sa.Column("protocol", sa.String(length=20), nullable=False,
                  server_default=sa.text("'wireguard'"), index=True),
        sa.Column("status", sa.String(length=20), nullable=False,
                  server_default=sa.text("'active'"), index=True),
        sa.Column("private_key", sa.Text(), nullable=True),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("preshared_key", sa.Text(), nullable=True),
        sa.Column("password", sa.String(length=255), nullable=True),
        sa.Column("assigned_ip", sa.String(length=45), nullable=True),
        sa.Column("dns_servers", sa.String(length=255), nullable=True),
        sa.Column("allowed_ips", sa.Text(), nullable=True),
        sa.Column("bandwidth_limit_bytes", sa.BigInteger(), nullable=True),
        sa.Column("bandwidth_used_bytes", sa.BigInteger(), nullable=False,
                  server_default=sa.text("0")),
        sa.Column("max_connections", sa.Integer(), nullable=False,
                  server_default=sa.text("3")),
        sa.Column("server_id", postgresql.UUID(), nullable=True, index=True),
        sa.Column("provisioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_handshake_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_config", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_vpn_accounts_service_id_services",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["vpn_servers.id"],
            name="fk_vpn_accounts_server_id_vpn_servers",
            ondelete="SET NULL",
        ),
    )

    # -----------------------------------------------------------------------
    # 2. Create vpn_protocol_configs table
    # -----------------------------------------------------------------------
    op.create_table(
        "vpn_protocol_configs",
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        sa.Column("vpn_account_id", postgresql.UUID(), nullable=False, index=True),
        sa.Column("config_key", sa.String(length=100), nullable=False),
        sa.Column("config_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["vpn_account_id"],
            ["vpn_accounts.id"],
            name="fk_vpn_protocol_configs_account_id_vpn_accounts",
            ondelete="CASCADE",
        ),
    )

    # -----------------------------------------------------------------------
    # 3. Create vpn_sessions table
    # -----------------------------------------------------------------------
    op.create_table(
        "vpn_sessions",
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        sa.Column("vpn_account_id", postgresql.UUID(), nullable=False, index=True),
        sa.Column("status", sa.String(length=20), nullable=False,
                  server_default=sa.text("'connected'"), index=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.Column("client_port", sa.Integer(), nullable=True),
        sa.Column("bytes_sent", sa.BigInteger(), nullable=False,
                  server_default=sa.text("0")),
        sa.Column("bytes_received", sa.BigInteger(), nullable=False,
                  server_default=sa.text("0")),
        sa.Column("server_endpoint", sa.String(length=255), nullable=True),
        sa.Column("disconnect_reason", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["vpn_account_id"],
            ["vpn_accounts.id"],
            name="fk_vpn_sessions_account_id_vpn_accounts",
            ondelete="CASCADE",
        ),
    )

    # -----------------------------------------------------------------------
    # 4. Create indexes for common query patterns
    # -----------------------------------------------------------------------
    op.create_index("ix_vpn_accounts_protocol_status", "vpn_accounts",
                    ["protocol", "status"])
    op.create_index("ix_vpn_sessions_account_status", "vpn_sessions",
                    ["vpn_account_id", "status"])
    op.create_index("ix_vpn_protocol_configs_account_key", "vpn_protocol_configs",
                    ["vpn_account_id", "config_key"])


def downgrade() -> None:
    """
    Drop vpn_sessions, vpn_protocol_configs, and vpn_accounts tables.
    """
    # Drop indexes first
    op.drop_index("ix_vpn_protocol_configs_account_key", table_name="vpn_protocol_configs")
    op.drop_index("ix_vpn_sessions_account_status", table_name="vpn_sessions")
    op.drop_index("ix_vpn_accounts_protocol_status", table_name="vpn_accounts")

    # Drop tables
    op.drop_table("vpn_sessions")
    op.drop_table("vpn_protocol_configs")
    op.drop_table("vpn_accounts")
