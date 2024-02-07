"""User model."""
import os

import asyncpg
from pydantic import BaseModel


class User(BaseModel):
    """User model."""

    id: int
    email: str
    is_active: bool | None = False

    @classmethod
    async def create(cls: "User", email: str) -> "User":
        """Create a user."""
        conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
        user = await conn.fetchrow("INSERT INTO users (email) VALUES ($1) RETURNING *", email)
        return cls(**user)

    @classmethod
    async def get(cls: "User", user_id: int) -> "User":
        """Get a user by id."""
        conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
        user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        return cls(**user)

    @classmethod
    async def get_by_email(cls: "User", email: str) -> "User | None":
        """Get a user by email."""
        conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
        user = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)
        if not user:
            return None
        return cls(**user)

    async def activate(self: "User") -> "User":
        """Activate the user."""
        conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
        await conn.execute("BEGIN")
        await conn.execute("UPDATE users SET is_active = TRUE WHERE id = $1", self.id)
        await conn.execute("COMMIT")
        self.is_active = True
        return self
