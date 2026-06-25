"""Check what tables exist in the database."""
import os

import psycopg2

raw_url = os.environ["DB_URL_SYNC"]
# Convert SQLAlchemy-style URL to psycopg2 DSN
dsn = raw_url.replace("postgresql+psycopg2://", "postgresql://")
conn = psycopg2.connect(dsn)
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)
cur.execute("SELECT version_num FROM alembic_version")
print("Alembic version:", cur.fetchall())
cur.close()
conn.close()
