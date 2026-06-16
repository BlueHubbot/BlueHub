"""
Script to generate an Alembic migration file for the initial schema.
Uses SQLAlchemy's PostgreSQL DDL compiler to produce CREATE TABLE statements.
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import MetaData, create_engine
from sqlalchemy.dialects.postgresql import pyscopg2 as postgresql_dialect

# Import all models to register them with CoreBase.metadata
from shared.models import CoreBase


def generate_create_table_statements(metadata: MetaData) -> str:
    """Generate CREATE TABLE statements for all tables in the metadata.

    Uses the PostgreSQL dialect to render proper DDL for PostgreSQL-specific
    types like JSONB, UUID(as_uuid=True), etc.
    """
    dialect = postgresql_dialect.dialect()

    # Create a dummy engine with PostgreSQL dialect just for compilation
    engine = create_engine(
        "postgresql+psycopg2://",
        module=lambda: None,  # dummy module
    )
    engine.dialect = dialect

    statements = []

    # Sort tables by name for deterministic output
    sorted_tables = sorted(metadata.tables.values(), key=lambda t: t.name)

    for table in sorted_tables:
        # Create the CREATE TABLE statement
        compiled = table.create(bind=engine, checkfirst=False)
        statements.append(str(compiled.compile(dialect=dialect)))

    return "\n\n".join(statements)


def create_initial_migration() -> None:
    """Create the initial Alembic migration file."""
    metadata = CoreBase.metadata

    # Generate the CREATE TABLE SQL
    generate_create_table_statements(metadata)

    # Generate a unique revision ID
    revision_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    down_revision = None  # This is the initial migration

    # Count the tables
    table_count = len(metadata.tables)
    table_names = sorted(metadata.tables.keys())

    # Generate the migration script
    migration_content = f'''"""
BlueHub Initial Schema
========================

Create initial database schema for BlueHub platform.
Contains all core tables for multi-tenant operation.

Revision ID: {revision_id}
Revises: {down_revision}
Create Date: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f") + " (UTC)"}
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "{revision_id}"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create the initial schema with {table_count} tables:
    {chr(10) + "    ".join(f"- {name}" for name in table_names)}
    """

    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

{_generate_upgrade_ops(metadata)}


def downgrade() -> None:
    """
    Drop all tables to revert to empty state.
    Tables are dropped in reverse dependency order.
    """

{_generate_downgrade_ops(metadata)}

'''

    # Write the migration file
    versions_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alembic", "versions")
    os.makedirs(versions_dir, exist_ok=True)

    filename = f"{revision_id}_initial_schema.py"
    filepath = os.path.join(versions_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(migration_content)

    print(f"Migration created: {filepath}")
    print(f"Tables ({table_count}):")
    for name in table_names:
        print(f"  - {name}")


def _get_column_type(col) -> str:
    """Get the Alembic-compatible type string for a column."""
    col_type = col.type
    type_str = str(col_type)

    # Map SQLAlchemy types to Alembic type representations
    if "JSONB" in type_str:
        return "postgresql.JSONB"
    if "UUID" in type_str:
        return "postgresql.UUID()"
    if "BIGINT" in type_str.upper() or "BigInteger" in type_str:
        return "sa.BigInteger()"
    if "BOOLEAN" in type_str.upper() or type_str == "BOOLEAN":
        return "sa.Boolean()"
    if "INTEGER" in type_str.upper() or type_str == "INTEGER":
        return "sa.Integer()"
    if "TEXT" in type_str.upper() or type_str == "TEXT":
        return "sa.Text()"
    if "FLOAT" in type_str.upper() or type_str == "FLOAT":
        return "sa.Float()"
    if "VARCHAR" in type_str.upper():
        # Extract length
        import re
        match = re.search(r"VARCHAR\((\d+)\)", type_str)
        if match:
            return f"sa.String(length={match.group(1)})"
        return "sa.String()"
    if "DATETIME" in type_str.upper() or "TIMESTAMP" in type_str.upper():
        return "sa.DateTime(timezone=True)"
    if "NullType" in type_str:
        return "sa.String()"

    return f"sa.{type_str}()"


def _generate_upgrade_ops(metadata):
    """Generate Alembic upgrade operations for table creation."""

    ops = []

    # Build dependency graph to order tables (parents first)
    sorted_tables = sorted(metadata.tables.values(), key=lambda t: t.name)

    for table in sorted_tables:
        cols = []
        constraints = []

        for col in table.columns:
            col_lines = _generate_column_op(col)
            cols.extend(col_lines)

            # Collect foreign keys for this column
            for fk in col.foreign_keys:
                constraints.append(
                    f'        sa.ForeignKeyConstraint(\n'
                    f'            ["{col.name}"],\n'
                    f'            ["{fk.column.table.name}.{fk.column.name}"],\n'
                    f'            name="fk_{table.name}_{col.name}_{fk.column.table.name}",\n'
                    f'        )'
                )

        # Build the create_table call
        table_op = '    op.create_table(\n'
        table_op += f'        "{table.name}",\n'
        table_op += ",\n".join(cols)
        if constraints:
            table_op += ",\n" + ",\n".join(constraints)
        table_op += '\n    )\n'
        ops.append(table_op)

    return "\n".join(ops)


def _generate_column_op(col):
    """Generate a single column definition line."""
    lines = []

    nullable = col.nullable
    is_pk = col.primary_key
    server_default = col.server_default

    # Determine type
    type_str = _get_column_type(col)

    # Build column args
    args = [f'        sa.Column("{col.name}", {type_str}']

    if is_pk:
        args.append("primary_key=True")

    if not nullable:
        args.append("nullable=False")
    else:
        args.append("nullable=True")

    if server_default is not None:
        default_text = str(server_default.arg) if hasattr(server_default, 'arg') else str(server_default)
        args.append(f'server_default=sa.text("{default_text}")')

    if col.unique:
        args.append("unique=True")

    if col.index:
        args.append("index=True")

    if col.autoincrement:
        args.append("autoincrement=True")

    if col.default is not None and not server_default:
        args.append(f'default={col.default.arg}')

    args.append(")")
    lines.append(",\n".join(args))

    return lines


def _generate_downgrade_ops(metadata):
    """Generate Alembic downgrade operations for table dropping.

    Tables are dropped in reverse dependency order (children before parents).
    """
    # Build reverse dependency order
    tables = list(metadata.tables.values())

    # Start with all tables, order by dependency
    ordered = []

    def get_deps(table):
        """Get tables that this table depends on via foreign keys."""
        deps = set()
        for col in table.columns:
            for fk in col.foreign_keys:
                if fk.column.table.name != table.name:
                    deps.add(fk.column.table)
        return deps

    # Topological sort (parents before children)
    remaining = set(tables)
    while remaining:
        # Find tables whose deps are all already dropped or are self-referencing
        available = {t for t in remaining if not get_deps(t) - remaining}
        if not available:
            # Fall back to remaining (circular deps)
            available = remaining.copy()
        for t in sorted(available, key=lambda x: x.name, reverse=True):
            ordered.append(t)
            remaining.remove(t)

    # Reverse for drop order (children before parents)
    ordered.reverse()

    ops = []
    for table in ordered:
        ops.append(f'    op.drop_table("{table.name}")')

    return "\n".join(ops)


if __name__ == "__main__":
    create_initial_migration()
