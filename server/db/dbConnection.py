import logging
import os
import threading
import time
from contextlib import contextmanager

from dotenv import load_dotenv
from psycopg2 import extras
from psycopg2.pool import ThreadedConnectionPool

load_dotenv()

logger = logging.getLogger(__name__)

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

_pool: ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()


def _pool_min_max() -> tuple[int, int]:
    try:
        mn = int(os.getenv("DB_POOL_MIN_CONN", "1"))
    except ValueError:
        mn = 1
    try:
        mx = int(os.getenv("DB_POOL_MAX_CONN", "20"))
    except ValueError:
        mx = 20
    mn = max(1, mn)
    mx = max(mn, mx)
    return mn, mx


def get_connection_pool() -> ThreadedConnectionPool:
    """Return the process-wide threaded connection pool (lazy init)."""
    global _pool
    if _pool is not None:
        return _pool
    with _pool_lock:
        if _pool is not None:
            return _pool
        mn, mx = _pool_min_max()
        _pool = ThreadedConnectionPool(
            mn,
            mx,
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME,
        )
        logger.info("DB connection pool initialized min=%s max=%s", mn, mx)
        return _pool


def close_connection_pool() -> None:
    """Close all pool connections (call from app shutdown)."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            try:
                _pool.closeall()
                logger.info("DB connection pool closed")
            except Exception as e:
                logger.warning("Error closing DB pool: %s", e)
            _pool = None


@contextmanager
def get_connection():
    """
    Check out a connection from the pool and return it on exit.
    Rolls back on exception; does not commit (use get_dict_cursor for transactions).
    """
    pool = get_connection_pool()
    t0 = time.perf_counter()
    conn = pool.getconn()
    wait_ms = (time.perf_counter() - t0) * 1000.0
    if wait_ms > 500 and logger.isEnabledFor(logging.WARNING):
        logger.warning("DB pool checkout slow: %.1fms", wait_ms)
    try:
        yield conn
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            pool.putconn(conn)
        except Exception as e:
            logger.error("Failed to return connection to pool: %s", e)


@contextmanager
def get_dict_cursor():
    """RealDictCursor with commit on success, rollback on error."""
    with get_connection() as conn:
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                yield cur
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
