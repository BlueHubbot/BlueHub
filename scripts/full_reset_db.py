"""Full database reset - drop all tables, enums, and types."""
import psycopg2

conn = psycopg2.connect("postgresql://postgres:postgres@bluehub-postgres:5432/bluehub")
conn.autocommit = True
cur = conn.cursor()

# 1. Drop all tables (except alembic_version, handled last)
cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
      AND table_name != 'alembic_version'
""")
tables = [r[0] for r in cur.fetchall()]
for t in tables:
    cur.execute(f'DROP TABLE IF EXISTS "{t}" CASCADE')
    print(f"  Dropped table: {t}")

# 2. Drop all enum types
cur.execute("""
    SELECT typname
    FROM pg_type
    WHERE typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
      AND typtype = 'e'
""")
types = [r[0] for r in cur.fetchall()]
for t in types:
    cur.execute(f'DROP TYPE IF EXISTS "{t}" CASCADE')
    print(f"  Dropped type: {t}")

# 3. Drop alembic_version last
cur.execute("DROP TABLE IF EXISTS alembic_version CASCADE")
print("  Dropped alembic_version")

cur.close()
conn.close()
print("Full database reset complete!")
