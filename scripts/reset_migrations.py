"""Reset alembic_version table so migrations run from scratch."""
import os

import psycopg2

raw_url = os.environ["DB_URL_SYNC"]
dsn = raw_url.replace("postgresql+psycopg2://", "postgresql://")
conn = psycopg2.connect(dsn)
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS alembic_version CASCADE")
conn.commit()
print("alembic_version table dropped")
cur.close()
conn.close()
