"""
BlueHub VPS Module Tables
==========================

Add VPS-related tables: vps_instances, vps_snapshots, and the vpspowerstatus enum.

Tables created:
    - vps_instances : VPS virtual machine instances per service
    - vps_snapshots : Backup snapshots per VPS instance

Enums created:
    - vpspowerstatus : running, stopped, suspended

Revision ID: 20260615_201200
Revises: 20260614_201944
Create Date: 2026-06-15 20:12:00.000000 (UTC+3:30)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260615_201200"
down_revision: str | None = "20260614_201944"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create VPS enum type, vps_instances table, and vps_snapshots table.
    """
    # -----------------------------------------------------------------------
    # 0. Create vpspowerstatus enum type
    # -----------------------------------------------------------------------
    vpspowerstatus_enum = sa.Enum(
        "running", "stopped", "suspended", name="vpspowerstatus"
    )
    vpspowerstatus_enum.create(op.get_bind(), checkfirst=True)

    # -----------------------------------------------------------------------
    # 1. Create vps_instances table
    # -----------------------------------------------------------------------
    op.create_table(
        "vps_instances",
        # Primary key (from UUIDMixin)
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        # FK to services
        sa.Column(
            "service_id",
            postgresql.UUID(),
            sa.ForeignKey("services.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        # Proxmox reference
        sa.Column("proxmox_vmid", sa.Integer(), nullable=True, unique=True),
        sa.Column("proxmox_node", sa.String(length=100), nullable=True),
        # Resource allocation
        sa.Column(
            "cpu_cores",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "memory_mb",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1024"),
        ),
        sa.Column(
            "disk_gb",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("25"),
        ),
        sa.Column(
            "bandwidth_limit_mbps",
            sa.Integer(),
            nullable=True,
        ),
        # Power and status
        sa.Column(
            "power_status",
            vpspowerstatus_enum,
            nullable=False,
            server_default=sa.text("'stopped'"),
            index=True,
        ),
        # Networking
        sa.Column("primary_ipv4", sa.String(length=45), nullable=True),
        sa.Column("primary_ipv6", sa.String(length=45), nullable=True),
        # OS / template info
        sa.Column("os_template", sa.String(length=100), nullable=True),
        sa.Column("root_password", sa.String(length=255), nullable=True),
        # Provisioning metadata
        sa.Column(
            "provisioned_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_power_change_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Traffic counters
        sa.Column(
            "bandwidth_used_bytes",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        # VNC / Console access
        sa.Column("vnc_port", sa.Integer(), nullable=True),
        sa.Column("vnc_password", sa.String(length=255), nullable=True),
        # Extra metadata
        sa.Column(
            "extra_config",
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        # Timestamps (from TimestampMixin)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # -----------------------------------------------------------------------
    # 2. Create vps_snapshots table
    # -----------------------------------------------------------------------
    op.create_table(
        "vps_snapshots",
        # Primary key (from UUIDMixin)
        sa.Column("id", postgresql.UUID(), primary_key=True, nullable=False),
        # FK to vps_instances
        sa.Column(
            "vps_instance_id",
            postgresql.UUID(),
            sa.ForeignKey("vps_instances.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Snapshot metadata
        sa.Column("snapshot_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "is_ram_included",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "snapshot_taken_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Timestamps (from TimestampMixin)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # -----------------------------------------------------------------------
    # 3. Composite indexes for common query patterns
    # -----------------------------------------------------------------------
    op.create_index(
        "ix_vps_instances_power_status",
        "vps_instances",
        ["power_status"],
    )
    op.create_index(
        "ix_vps_snapshots_instance_snapshot",
        "vps_snapshots",
        ["vps_instance_id", "snapshot_name"],
    )


def downgrade() -> None:
    """
    Drop vps_snapshots and vps_instances tables, then the enum type.
    """
    # Drop indexes first
    op.drop_index(
        "ix_vps_snapshots_instance_snapshot",
        table_name="vps_snapshots",
    )
    op.drop_index(
        "ix_vps_instances_power_status",
        table_name="vps_instances",
    )

    # Drop tables
    op.drop_table("vps_snapshots")
    op.drop_table("vps_instances")

    # Drop enum type
    sa.Enum(
        "running", "stopped", "suspended", name="vpspowerstatus"
    ).drop(op.get_bind(), checkfirst=True)
