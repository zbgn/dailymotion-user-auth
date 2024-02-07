"""Token model."""

import datetime
import os

import asyncpg
import pytz
from pydantic import BaseModel


class Token(BaseModel):
    """Token model."""

    id: int
    code: str
    user_id: int
    valid_until: datetime.datetime

    @property
    def is_valid(self: "Token") -> bool:
        """Check if the token is valid."""
        return self.valid_until.replace(tzinfo=None) > datetime.datetime.now(tz=pytz.utc).replace(tzinfo=None)

    @classmethod
    async def create(cls: "Token", code: str, user_id: int) -> "Token":
        """Create a token."""
        conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
        await conn.execute("BEGIN")
        token = await conn.fetchrow(
            "INSERT INTO tokens (code, user_id, valid_until) VALUES ($1, $2, $3) RETURNING *",
            code,
            user_id,
            datetime.datetime.now(tz=pytz.utc).replace(tzinfo=None) + datetime.timedelta(minutes=1),
        )
        await conn.execute("COMMIT")
        return cls(**token)

    @classmethod
    async def get(cls: "Token", token_id: int) -> "Token":
        """Get a token by id."""
        conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
        token = await conn.fetchrow("SELECT * FROM tokens WHERE id = $1", token_id)
        return cls(**token)

    @classmethod
    async def get_by_code(cls: "Token", code: str) -> "Token":
        """Get a token by code."""
        conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
        token = await conn.fetchrow("SELECT * FROM tokens WHERE code = $1", code)
        return cls(**token)

    @classmethod
    async def get_by_user_email(cls: "Token", user_email: str) -> "Token":
        """Get a token by user id."""
        conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
        token = await conn.fetchrow(
            "SELECT * FROM tokens WHERE user_id = (SELECT id FROM users WHERE email = $1) "
            "ORDER BY valid_until DESC LIMIT 1",
            user_email,
        )
        return cls(**token)

    @classmethod
    async def delete(cls: "Token") -> bool:
        """Delete a token."""
        conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
        await conn.execute("DELETE FROM tokens WHERE id = $1", cls.id)
        return True
