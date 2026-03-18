"""Repository for activation token persistence operations."""

import datetime

import asyncpg
import pytz

from app.infrastructure.db import get_db_connection
from app.infrastructure.settings import get_settings
from app.models.token import Token


class ActivationTokenRepository:
    """Activation token data access using explicit SQL and asyncpg."""

    def __init__(self, database_url: str | None = None) -> None:
        """Initialize repository with an optional database URL override."""
        self.database_url = database_url or get_settings().database_url

    async def create(
        self,
        code: str,
        user_id: int,
        conn: asyncpg.Connection | None = None,
    ) -> Token:
        """Create a token for a user."""
        owns_connection = conn is None
        if conn is None:
            conn = await get_db_connection(self.database_url)
        try:
            token = await conn.fetchrow(
                "INSERT INTO tokens (code, user_id, valid_until) VALUES ($1, $2, $3) RETURNING *",
                code,
                user_id,
                datetime.datetime.now(tz=pytz.utc).replace(tzinfo=None) + datetime.timedelta(minutes=1),
            )
            return Token(**token)
        finally:
            if owns_connection:
                await conn.close()

    async def get_by_user_email(
        self,
        user_email: str,
        conn: asyncpg.Connection | None = None,
    ) -> Token | None:
        """Get latest token by user email."""
        owns_connection = conn is None
        if conn is None:
            conn = await get_db_connection(self.database_url)
        try:
            token = await conn.fetchrow(
                "SELECT * FROM tokens WHERE user_id = (SELECT id FROM users WHERE email = $1) "
                "ORDER BY valid_until DESC LIMIT 1",
                user_email,
            )
            if not token:
                return None
            return Token(**token)
        finally:
            if owns_connection:
                await conn.close()

    async def invalidate_for_user(self, user_id: int, conn: asyncpg.Connection | None = None) -> None:
        """Invalidate all activation tokens for a user."""
        owns_connection = conn is None
        if conn is None:
            conn = await get_db_connection(self.database_url)
        try:
            await conn.execute(
                "UPDATE tokens SET valid_until = $2 WHERE user_id = $1",
                user_id,
                datetime.datetime.now(tz=pytz.utc).replace(tzinfo=None),
            )
        finally:
            if owns_connection:
                await conn.close()
