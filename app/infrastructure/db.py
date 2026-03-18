"""Shared database access entry points."""

import asyncpg

from app.infrastructure.settings import get_settings

_db_state: dict[str, asyncpg.Pool | None] = {"pool": None}


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


async def get_db_connection(database_url: str | None = None) -> asyncpg.Connection:
    """Return a direct connection (incremental step before pooled DI)."""
    if database_url is None:
        database_url = get_settings().database_url
    return await asyncpg.connect(database_url)
