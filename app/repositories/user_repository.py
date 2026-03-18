"""Repository for user persistence operations."""

import os

import asyncpg

from app.models.user import User


class UserRepository:
    """User data access using explicit SQL and asyncpg."""

    def __init__(self, database_url: str | None = None) -> None:
        """Initialize repository with an optional database URL override."""
        self.database_url = database_url or os.environ.get("DATABASE_URL")

    async def create(self, email: str, password: str) -> User:
        """Create a user and return the persisted projection."""
        conn = await asyncpg.connect(self.database_url)
        try:
            hashed_password = await conn.fetchval("SELECT crypt($1, gen_salt('bf'))", password)
            user = await conn.fetchrow(
                "INSERT INTO users (email, password) VALUES ($1, $2) RETURNING id, email, is_active",
                email,
                hashed_password,
            )
            return User(**user)
        finally:
            await conn.close()

    async def exists(self, email: str) -> bool:
        """Check if a user exists by email."""
        conn = await asyncpg.connect(self.database_url)
        try:
            user = await conn.fetchval("SELECT id FROM users WHERE email = $1", email)
            return bool(user)
        finally:
            await conn.close()

    async def get_by_email(self, email: str, password: str) -> User:
        """Get user by email if password is valid."""
        if not await self.exists(email):
            msg = "User not found"
            raise ValueError(msg)

        conn = await asyncpg.connect(self.database_url)
        try:
            user = await conn.fetchrow(
                "SELECT id, email, is_active FROM users WHERE email = $1 and password = crypt($2, password)",
                email,
                password,
            )
            if not user:
                msg = "Incorrect password"
                raise ValueError(msg)
            return User(**user)
        finally:
            await conn.close()

    async def activate(self, user_id: int) -> User:
        """Activate a user and return the updated projection."""
        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute("UPDATE users SET is_active = TRUE WHERE id = $1", user_id)
            user = await conn.fetchrow("SELECT id, email, is_active FROM users WHERE id = $1", user_id)
            return User(**user)
        finally:
            await conn.close()
