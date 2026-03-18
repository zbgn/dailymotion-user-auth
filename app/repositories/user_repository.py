"""Repository for user persistence operations."""

import asyncpg

from app.infrastructure.db import get_db_connection
from app.infrastructure.settings import get_settings
from app.models.user import User


class UserRepository:
    """User data access using explicit SQL and asyncpg."""

    def __init__(self, database_url: str | None = None) -> None:
        """Initialize repository with an optional database URL override."""
        self.database_url = database_url or get_settings().database_url

    async def create(
        self,
        email: str,
        password: str,
        conn: asyncpg.Connection | None = None,
    ) -> User:
        """Create a user and return the persisted projection."""
        owns_connection = conn is None
        if conn is None:
            conn = await get_db_connection(self.database_url)
        try:
            hashed_password = await conn.fetchval("SELECT crypt($1, gen_salt('bf'))", password)
            user = await conn.fetchrow(
                "INSERT INTO users (email, password) VALUES ($1, $2) RETURNING id, email, is_active",
                email,
                hashed_password,
            )
            return User(**user)
        finally:
            if owns_connection:
                await conn.close()

    async def exists(self, email: str, conn: asyncpg.Connection | None = None) -> bool:
        """Check if a user exists by email."""
        owns_connection = conn is None
        if conn is None:
            conn = await get_db_connection(self.database_url)
        try:
            user = await conn.fetchval("SELECT id FROM users WHERE email = $1", email)
            return bool(user)
        finally:
            if owns_connection:
                await conn.close()

    async def get_by_email(
        self,
        email: str,
        password: str,
        conn: asyncpg.Connection | None = None,
    ) -> User:
        """Get user by email if password is valid."""
        if not await self.exists(email, conn=conn):
            msg = "User not found"
            raise ValueError(msg)

        owns_connection = conn is None
        if conn is None:
            conn = await get_db_connection(self.database_url)
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
            if owns_connection:
                await conn.close()

    async def activate(self, user_id: int, conn: asyncpg.Connection | None = None) -> User:
        """Activate a user and return the updated projection."""
        owns_connection = conn is None
        if conn is None:
            conn = await get_db_connection(self.database_url)
        try:
            await conn.execute("UPDATE users SET is_active = TRUE WHERE id = $1", user_id)
            user = await conn.fetchrow("SELECT id, email, is_active FROM users WHERE id = $1", user_id)
            return User(**user)
        finally:
            if owns_connection:
                await conn.close()
