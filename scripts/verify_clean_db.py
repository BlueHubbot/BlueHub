"""Verify the database is clean."""
import psycopg2

conn = psycopg2.connect("postgresql://postgres:postgres@bluehub-postgres:5432/bluehub")
cur = conn.cursor()

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
tables = [t[0] for t in cur.fetchall()]
print(f"Tables ({len(tables)}): {tables}")

cur.execute("SELECT typname FROM pg_type WHERE typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public') AND typtype = 'e'")
types = [t[0] for t in cur.fetchall()]
print(f"Enums ({len(types)}): {types}")

cur.close()
conn.close()

if not tables and not types:
    print("Database is CLEAN!")
else:
    print("Database is NOT clean.")
