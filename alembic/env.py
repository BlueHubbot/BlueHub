"""
BlueHub Alembic Environment Configuration
==========================================
Configures Alembic to use the project's database settings and
auto-detect model changes for migration generation.
Supports both offline mode (for SQL script generation) and
online mode (for direct database execution).
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, engine_from_config, pool, text

from alembic import context

# Ensure the project root is on sys.path so we can import bluehub modules
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Database URL Resolution
# ---------------------------------------------------------------------------
# Priority:
#   1. Environment variable DB_URL_SYNC (for explicit override)
#   2. Environment variable DATABASE_URL (async) -> converted to sync
#   3. Fallback default
#
# The default DATABASE_URL in the project is:
#   postgresql+asyncpg://postgres:postgres@localhost:5432/bluehub
# We convert it to psycopg2 for Alembic compatibility.
# ---------------------------------------------------------------------------

def _get_sync_db_url() -> str:
    """Resolve the sync database URL for Alembic migrations.

    Returns a psycopg2-based connection string suitable for Alembic.
    """
    # 1. Check for explicit sync URL override
    explicit = os.environ.get("DB_URL_SYNC")
    if explicit:
        return explicit

    # 2. Check DATABASE_URL (async) and convert to sync
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/bluehub",
    )
    return db_url.replace("+asyncpg", "+psycopg2")


# ---------------------------------------------------------------------------
# Model Imports
# ---------------------------------------------------------------------------
# Import all models so that Alembic can detect them for autogenerate.
# We need to import the base that contains all model metadata.
# NOTE: We avoid importing core.config here because it depends on
# pydantic-settings which may not be installed in all environments.
# Instead we resolve the DB URL from environment variables directly.
# Import module models so Alembic can detect them for autogenerate
import modules.vpn.models  # noqa: E402
import modules.vps.models  # noqa: E402, F401
import shared.models.audit_log  # noqa: E402
import shared.models.invoice  # noqa: E402
import shared.models.module_registry  # noqa: E402
import shared.models.product  # noqa: E402
import shared.models.service  # noqa: E402

# Import all model modules to register them with CoreBase.metadata
import shared.models.tenant  # noqa: E402
import shared.models.transaction  # noqa: E402
import shared.models.user  # noqa: E402, F401
from shared.models import CoreBase  # noqa: E402

# Set the target metadata for autogenerate support
target_metadata = CoreBase.metadata

# Override sqlalchemy.url in the alembic config with our sync database URL
_db_url = _get_sync_db_url()
config.set_main_option("sqlalchemy.url", _db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Ensure uuid-ossp extension exists for UUID generation
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


def run_autogenerate_offline() -> None:
    """Run autogenerate in offline mode using a temporary SQLite database.

    This allows ``alembic revision --autogenerate`` to work without a
    live PostgreSQL instance by using an in-memory SQLite database for
    metadata comparison. The generated migration script will target
    PostgreSQL (as configured in the database URL).

    Use this by setting the environment variable:
        AUTOGENERATE_OFFLINE=1
    """

    # Use SQLite in-memory database for autogenerate comparison
    temp_engine = create_engine("sqlite://", echo=False)
    target_metadata.create_all(temp_engine)

    # Now configure Alembic with the URL from config (for dialect awareness)
    config.get_main_option("sqlalchemy.url")

    # Connect to the temp engine and run migrations
    with temp_engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# Determine which migration runner to use
if context.is_offline_mode():
    run_migrations_offline()
elif os.environ.get("AUTOGENERATE_OFFLINE") == "1":
    run_autogenerate_offline()
else:
    run_migrations_online()
