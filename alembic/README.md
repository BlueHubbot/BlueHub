# BlueHub Database Migrations (Alembic)

## Overview

This directory contains Alembic-managed database migrations for the BlueHub platform.
Migrations track changes to the database schema over time, enabling version control,
rollback, and automated schema updates across environments.

**Schema Engine**: PostgreSQL 16+ (using psycopg2 for Alembic compatibility)
**Migration Status**: ✅ Initial schema created (revision `20260613_235959`)

---

## Prerequisites

- Python 3.10+
- PostgreSQL 16+ (local or remote)
- Alembic (installed via `pip install alembic` or project dependencies)
- Database URL configured (see below)

### Required Python Packages

```
alembic>=1.13.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0   # For Alembic sync connections
asyncpg>=0.29.0           # For application async connections
```

---

## Configuration

### Database URL Resolution

Alembic resolves the database connection string in the following priority order
(defined in `env.py`):

1. **`DB_URL_SYNC`** — Explicit sync URL override (highest priority)
   ```
   postgresql://user:password@host:5432/bluehub
   ```

2. **`DATABASE_URL`** — Async URL (auto-converted to sync)
   ```
   postgresql+asyncpg://user:password@host:5432/bluehub
   ```
   *(Alembic replaces `+asyncpg` with `+psycopg2` automatically)*

3. **Default fallback** (development):
   ```
   postgresql+asyncpg://postgres:postgres@localhost:5432/bluehub
   ```

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `DB_URL_SYNC` | Explicit sync URL for Alembic | `postgresql://postgres:postgres@localhost:5432/bluehub` |
| `DATABASE_URL` | Async URL used by the application | `postgresql+asyncpg://postgres:postgres@localhost:5432/bluehub` |
| `AUTOGENERATE_OFFLINE` | Enable offline autogenerate mode | Set to `1` to enable |

> **Note for Windows (cmd.exe):** Use `set VAR=value` to set environment variables.
> For PowerShell: `$env:VAR="value"`

---

## Migration Commands

### 1. Check Migration Status

View the current migration state and history:

```bash
# List all migrations with their status
alembic history

# Show the current revision of the database
alembic current

# Check migration state without connecting to a database
alembic heads
```

### 2. Run Migrations (Online Mode)

Apply pending migrations directly to a live PostgreSQL database:

```bash
# Apply all pending migrations
alembic upgrade head

# Apply a specific number of revisions
alembic upgrade +2

# Migrate to a specific revision
alembic upgrade <revision_id>
```

> **Important:** Online mode requires a running PostgreSQL instance. The database
> must exist before running migrations (`CREATE DATABASE bluehub` if needed).

### 3. Run Migrations (Offline Mode)

Generate SQL scripts for review or manual execution (no database connection required):

```bash
# Generate SQL for all pending migrations
alembic upgrade head --sql

# Generate SQL to a file
alembic upgrade head --sql > migration_script.sql
```

This outputs raw SQL statements that can be reviewed before applying, or executed
by a DBA with elevated privileges.

### 4. Rollback (Downgrade)

Revert the last applied migration:

```bash
# Rollback one revision
alembic downgrade -1

# Rollback to a specific revision
alembic downgrade <revision_id>

# Rollback to the beginning (empty database)
alembic downgrade base
```

### 5. Generate New Migrations (Autogenerate)

Create a new migration by comparing the current model state with the database:

**Online autogenerate** (requires live PostgreSQL):

```bash
alembic revision --autogenerate -m "description_of_change"
```

**Offline autogenerate** (no database required):

```bash
set AUTOGENERATE_OFFLINE=1
alembic revision --autogenerate -m "description_of_change"
```

The offline mode creates a temporary SQLite in-memory database to compare
model metadata against, generating the migration script targeting PostgreSQL syntax.

> **Limitations:** Autogenerate cannot detect all changes. Always review and
> manually adjust the generated migration before applying. Common manual edits
> include ENUM type creation/dropping, partial indexes, and complex defaults.

### 6. Create an Empty Migration (Manual)

For complex schema changes that autogenerate cannot handle:

```bash
alembic revision -m "description_of_change"
```

This creates an empty migration stub that you fill in manually with `op.create_table()`,
`op.add_column()`, `op.execute()`, etc.

---

## Migration File Structure

Generated migration files are stored in `alembic/versions/` and follow this format:

```
20260613_235959_initial_schema.py
├── revision        — Unique ID (timestamp-based)
├── down_revision   — Parent revision (None for initial)
├── upgrade()       — Schema changes to apply
└── downgrade()     — Reversal of upgrade()
```

### Naming Convention

```
<YYYYMMDD_HHMMSS>_<snake_case_description>.py
```

Example: `20260613_235959_initial_schema.py`

---

## ENUM Type Handling

BlueHub uses PostgreSQL ENUM types extensively. Since Alembic autogenerate does
not natively handle ENUM creation/dropping well, ENUMs are managed manually via
`op.execute()`:

```python
# Create ENUM
op.execute("CREATE TYPE userrole AS ENUM ('superadmin', 'admin', 'reseller', 'user')")

# Drop ENUM (after all dependent tables are dropped)
op.execute("DROP TYPE IF EXISTS userrole")
```

**Rule:** When adding a new ENUM type, always create it *before* any table that
references it, and drop it *after* all referencing tables are removed.

---

## PostgreSQL-Specific Features Used

| Feature | Usage |
|---------|-------|
| `uuid-ossp` extension | UUID generation (`gen_random_uuid()`) |
| `postgresql.UUID` | Primary key columns |
| `postgresql.JSONB` | Flexible metadata, i18n, config storage |
| ENUM types | User roles, service statuses, billing cycles, etc. |
| Partial unique indexes | Business rule enforcement |
| Composite indexes | Query optimization for common patterns |

---

## Troubleshooting

### "FATAL: database does not exist"

Create the database first:

```bash
psql -U postgres -c "CREATE DATABASE bluehub;"
```

### "relation does not exist" during rollback

Ensure you are rolling back in the correct order. Tables must be dropped in
reverse dependency order (children before parents). The migration file handles
this automatically, but if you manually modify the downgrade, verify the order.

### Autogenerate produces incomplete ENUM handling

Autogenerate does not detect `sa.Enum` with `create_type=False`. After generating
a migration, manually add or remove ENUM types using `op.execute()` calls.

### Autogenerate does not detect partial indexes

Partial unique indexes (e.g., `WHERE active = true`) are not detected by autogenerate.
Add them manually using `op.create_index()` with `postgresql_where=` parameter.

### "sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UniqueViolation)"

The migration may conflict with existing data. Review migration history and
ensure the target database is in a consistent state:

```bash
alembic history
alembic current
```

### Offline SQL mode produces no output

If `alembic upgrade head --sql` produces no output, ensure:
1. The migration file has proper `upgrade()` and `downgrade()` functions
2. The `sqlalchemy.url` in `alembic.ini` is correctly set
3. Try running with verbose output: `alembic -v upgrade head --sql`

---

## Verification

Use the verification script to validate migration files without connecting to a
database:

```bash
python scripts/verify_migration.py
```

This runs 4 checks:
1. **Import** — Migration module loads with correct revision identifiers
2. **Balance** — All CREATE/DROP operations are paired correctly
3. **SQL Gen** — SQL generation is attempted (monkey-patched context)
4. **Downgrade** — Downgrade table order is exact reverse of upgrade

---

## Workflow Summary

```mermaid
graph TD
    A[Modify SQLAlchemy models] --> B{Autogenerate?}
    B -->|Yes| C[Set AUTOGENERATE_OFFLINE=1]
    B -->|No| D[alembic revision -m "desc"]
    C --> E[alembic revision --autogenerate -m "desc"]
    E --> F[Review & edit generated file]
    D --> F
    F --> G[Run python scripts/verify_migration.py]
    G --> H{All tests pass?}
    H -->|Yes| I[Apply: alembic upgrade head]
    H -->|No| J[Fix migration file]
    J --> F
    I --> K[Test application against DB]
```

---

## File Reference

| File | Purpose |
|------|---------|
| `alembic.ini` | Alembic configuration (DB URL, script location) |
| `alembic/env.py` | Environment setup, model imports, migration runner |
| `alembic/README.md` | This documentation |
| `alembic/versions/` | Migration revision files |
| `alembic/versions/20260613_235959_initial_schema.py` | Initial schema migration |
| `scripts/verify_migration.py` | Offline migration verification |
| `scripts/generate_migration.py` | Helper script for migration generation |

---

## Revision History

| Revision ID | Date | Description |
|-------------|------|-------------|
| `20260613_235959` | 2026-06-13 | Initial schema (8 tables, 5 ENUMs) |