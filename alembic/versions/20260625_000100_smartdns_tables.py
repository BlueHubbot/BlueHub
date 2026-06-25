"""
BlueHub SmartDNS Module Tables
===============================

Add SmartDNS-related tables: smartdns_profiles, dns_records.

Tables created:
    - smartdns_profiles : SmartDNS profile per service (one-to-one)
    - dns_records : Individual DNS records within a profile

Revision ID: 20260625_000100
Revises: 20260620_021230
Create Date: 2026-06-25 00:01:00.000000 (UTC+3:30)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260625_000100"
down_revision: str | None = "20260620_021230"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create smartdns_profiles and dns_records tables."""
    op.create_table(
        "smartdns_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "service_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("services.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "profile_name",
            sa.String(100),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="provisioning",
        ),
        sa.Column(
            "pdns_zone_id",
            sa.String(100),
            nullable=True,
        ),
        sa.Column(
            "pdns_zone_name",
            sa.String(255),
            nullable=True,
        ),
        sa.Column(
            "upstream_dns",
            sa.String(255),
            nullable=True,
            server_default="8.8.8.8",
        ),
        sa.Column(
            "geo_region",
            sa.String(50),
            nullable=True,
        ),
        sa.Column(
            "allowed_ips",
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "max_queries_per_second",
            sa.Integer(),
            nullable=True,
            server_default="100",
        ),
        sa.Column(
            "enable_dnssec",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "enable_logging",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "enable_ad_blocking",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "total_queries",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "extra_config",
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
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
    op.create_index(
        "ix_smartdns_profiles_service_id",
        "smartdns_profiles",
        ["service_id"],
    )
    op.create_index(
        "ix_smartdns_profiles_status",
        "smartdns_profiles",
        ["status"],
    )
    op.create_index(
        "ix_smartdns_profiles_pdns_zone_id",
        "smartdns_profiles",
        ["pdns_zone_id"],
    )
    op.create_index(
        "ix_smartdns_profiles_geo_region",
        "smartdns_profiles",
        ["geo_region"],
    )

    op.create_table(
        "dns_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("smartdns_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "record_type",
            sa.String(10),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "content",
            sa.String(500),
            nullable=False,
        ),
        sa.Column(
            "ttl",
            sa.Integer(),
            nullable=False,
            server_default="300",
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=True,
            server_default="0",
        ),
        sa.Column(
            "pdns_record_id",
            sa.String(100),
            nullable=True,
        ),
        sa.Column(
            "synced",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "disabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
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
    op.create_index(
        "ix_dns_records_profile_id",
        "dns_records",
        ["profile_id"],
    )


def downgrade() -> None:
    """Drop smartdns_profiles and dns_records tables."""
    op.drop_table("dns_records")
    op.drop_table("smartdns_profiles")