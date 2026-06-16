-- =============================================================================
-- Paymenter MySQL Database Initialization
-- =============================================================================
-- This script runs automatically when the mysql-paymenter container starts
-- for the first time. It sets up the character set and collation for Paymenter.
-- Paymenter's own migration system handles table creation.
-- =============================================================================

-- Set character set and collation for Paymenter (Laravel)
ALTER DATABASE paymenter CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create a dedicated schema if Paymenter uses it
-- (Paymenter typically uses the database directly, but we ensure proper config)
SELECT 'Paymenter database initialized successfully.' AS status;