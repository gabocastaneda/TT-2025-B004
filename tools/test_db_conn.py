from pathlib import Path
import sys
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

import mysql.connector as mc
from backend.db_config import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME

print("Trying:", DB_HOST, DB_PORT, DB_USER, DB_NAME, "pass=", repr(DB_PASS))
conn = mc.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME)
cur = conn.cursor()
cur.execute("SELECT @@version, CURRENT_USER()")
print(cur.fetchone())
conn.close()
print("OK: Python conectó a MySQL correctamente.")
