"""Shared database access entry points."""

import asyncpg

from app.infrastructure.settings import get_settings

_db_state: dict[str, asyncpg.Pool | None] = {"pool": None}


class _ManagedConnection:
    """Connection proxy that releases pooled connections on close."""

    def __init__(self, connection: asyncpg.Connection, pool: asyncpg.Pool | None = None) -> None:
        """Create a managed connection wrapper."""
        self._connection = connection
        self._pool = pool

    def __getattr__(self, name: str):  # noqa: ANN204
        """Delegate attribute access to the underlying connection."""
        return getattr(self._connection, name)

    async def close(self) -> None:
        """Release to pool when pooled, otherwise close the direct connection."""
        if self._pool is not None:
            await self._pool.release(self._connection)
            return
        await self._connection.close()


ManagedConnection = asyncpg.Connection | _ManagedConnection


async def create_db_pool() -> asyncpg.Pool:
    """Create and cache a database connection pool for future DI usage."""
    if _db_state["pool"] is None:
        settings = get_settings()
        _db_state["pool"] = await asyncpg.create_pool(settings.database_url)
    return _db_state["pool"]


async def close_db_pool() -> None:
    """Close the cached database connection pool if it exists."""
    pool = _db_state["pool"]
    if pool is not None:
        await pool.close()
        _db_state["pool"] = None


async def get_db_connection(database_url: str | None = None) -> ManagedConnection:
    """Return a managed connection, preferring the initialized pool when available."""
    settings = get_settings()
    pool = _db_state["pool"]

    if pool is not None and (database_url is None or database_url == settings.database_url):
        pooled_conn = await pool.acquire()
        return _ManagedConnection(pooled_conn, pool=pool)

    target_database_url = database_url or settings.database_url
    direct_conn = await asyncpg.connect(target_database_url)
    return _ManagedConnection(direct_conn)
