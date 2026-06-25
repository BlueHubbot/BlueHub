import sys

sys.path.insert(0, '.')
# The env variable is not used by this script - connect via localhost (host port mapping)

print('START', flush=True)

import psycopg2

try:
    conn = psycopg2.connect('postgresql://postgres:postgres@localhost:5432/bluehub')
    cur = conn.cursor()
    print('Connected!', flush=True)
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    rows = cur.fetchall()
    print('Tables:', [r[0] for r in rows], flush=True)
    cur.execute("SELECT version_num FROM alembic_version")
    ver = cur.fetchone()
    print('Alembic:', ver[0] if ver else 'NONE', flush=True)
    cur.close()
    conn.close()
except Exception as e:
    print(f'ERROR: {e}', flush=True)

print('END', flush=True)
