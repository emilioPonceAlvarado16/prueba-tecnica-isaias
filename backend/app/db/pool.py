from contextlib import contextmanager

from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings

_pool: ConnectionPool | None = None


def _configure(conn):
    register_vector(conn)


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row, "autocommit": True},
            configure=_configure,
            check=ConnectionPool.check_connection,   # Lambda congela el proceso: valida antes de usar
            open=True,
        )
    return _pool


@contextmanager
def connection():
    with get_pool().connection() as conn:
        yield conn


def fetch_all(sql: str, params=None) -> list[dict]:
    with connection() as conn:
        return conn.execute(sql, params).fetchall()


def fetch_one(sql: str, params=None) -> dict | None:
    with connection() as conn:
        return conn.execute(sql, params).fetchone()


def execute(sql: str, params=None) -> None:
    with connection() as conn:
        conn.execute(sql, params)
