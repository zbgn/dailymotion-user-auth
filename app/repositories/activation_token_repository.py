"""Repository for activation token persistence operations."""

import asyncpg

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
                "INSERT INTO tokens (code, user_id, valid_until) "
                "VALUES ($1, $2, (NOW() AT TIME ZONE 'UTC') + INTERVAL '1 minute') "
                "RETURNING *",
                code,
                user_id,
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

    async def get_by_user_email_and_code(
        self,
        user_email: str,
        code: str,
        conn: asyncpg.Connection | None = None,
    ) -> Token | None:
        """Get latest token matching user email and activation code."""
        owns_connection = conn is None
        if conn is None:
            conn = await get_db_connection(self.database_url)
        try:
            token = await conn.fetchrow(
                "SELECT * FROM tokens WHERE user_id = (SELECT id FROM users WHERE email = $1) "
                "AND code = $2 ORDER BY valid_until DESC LIMIT 1",
                user_email,
                code,
            )
            if not token:
                return None
            return Token(**token)
        finally:
            if owns_connection:
                await conn.close()

    async def get_valid_by_user_email_and_code(
        self,
        user_email: str,
        code: str,
        conn: asyncpg.Connection | None = None,
    ) -> Token | None:
        """Get latest non-expired token matching user email and activation code."""
        owns_connection = conn is None
        if conn is None:
            conn = await get_db_connection(self.database_url)
        try:
            token = await conn.fetchrow(
                "SELECT * FROM tokens WHERE user_id = (SELECT id FROM users WHERE email = $1) "
                "AND code = $2 AND valid_until > (NOW() AT TIME ZONE 'UTC') "
                "ORDER BY valid_until DESC LIMIT 1",
                user_email,
                code,
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
                "UPDATE tokens SET valid_until = (NOW() AT TIME ZONE 'UTC') WHERE user_id = $1",
                user_id,
            )
        finally:
            if owns_connection:
                await conn.close()

    async def delete_for_user(self, user_id: int, conn: asyncpg.Connection | None = None) -> None:
        """Delete all activation tokens for a user."""
        owns_connection = conn is None
        if conn is None:
            conn = await get_db_connection(self.database_url)
        try:
            await conn.execute("DELETE FROM tokens WHERE user_id = $1", user_id)
        finally:
            if owns_connection:
                await conn.close()
