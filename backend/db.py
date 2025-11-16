from contextlib import contextmanager
from mysql.connector import pooling
from .db_config import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME, POOL_NAME, POOL_SIZE

print("[DB] host=", DB_HOST, "port=", DB_PORT, "user=", DB_USER, "db=", DB_NAME)

_pool = None

def _ensure_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name=POOL_NAME,
            pool_size=POOL_SIZE,
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            autocommit=False,
        )

@contextmanager
def get_conn():
    _ensure_pool()
    conn = None
    try:
        conn = _pool.get_connection()
        yield conn
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
