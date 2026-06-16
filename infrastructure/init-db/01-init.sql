-- =============================================================================
-- BlueHub Database Initialization Script
-- =============================================================================
-- This script runs automatically when the PostgreSQL container starts
-- for the first time (via /docker-entrypoint-initdb.d/).
-- It creates the initial schema, extensions, and seed data.
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";        -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";          -- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pg_trgm";           -- Trigram text search (for indexes)
CREATE EXTENSION IF NOT EXISTS "citext";             -- Case-insensitive text type

-- Set default configuration for development
SET TIME ZONE 'UTC';

-- Create initial schema tracker table (Alembic will manage migrations)
-- This just ensures the database is ready for Alembic to run.
DO $$
BEGIN
    RAISE NOTICE 'BlueHub database initialization complete.';
    RAISE NOTICE 'Extensions enabled: uuid-ossp, pgcrypto, pg_trgm, citext';
    RAISE NOTICE 'Ready for Alembic migrations.';
END $$;