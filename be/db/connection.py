"""
connection.py — Async PostgreSQL connection pool (psycopg 3).
Routes get a connection via the `get_conn` dependency.
"""

import os
import sys

from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import CONFIG

CONNINFO = (
    f"host={CONFIG['host']} port={CONFIG['port']} dbname={CONFIG['dbname']} "
    f"user={CONFIG['user']} password={CONFIG['password']}"
)

# open=False → the pool is opened explicitly in the app lifespan, not at import time.
pool = AsyncConnectionPool(CONNINFO, min_size=1, max_size=10, open=False)


async def get_conn():
    """FastAPI dependency: yield a pooled async connection with dict rows."""
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        yield conn
