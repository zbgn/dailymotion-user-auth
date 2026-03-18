"""Repository for activation token persistence operations."""

import datetime

import pytz

from app.infrastructure.db import get_db_connection
from app.infrastructure.settings import get_settings
from app.models.token import Token


class ActivationTokenRepository:
    """Activation token data access using explicit SQL and asyncpg."""

    def __init__(self, database_url: str | None = None) -> None:
        """Initialize repository with an optional database URL override."""
        self.database_url = database_url or get_settings().database_url

    async def create(self, code: str, user_id: int) -> Token:
        """Create a token for a user."""
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
            await conn.close()

    async def get_by_user_email(self, user_email: str) -> Token | None:
        """Get latest token by user email."""
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
            await conn.close()
