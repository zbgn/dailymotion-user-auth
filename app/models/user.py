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
    async def create(cls: "User", email: str, password: str) -> "User":
        """Create a user."""
        conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
        try:
            hashed_password = await conn.fetchval("SELECT crypt($1, gen_salt('bf'))", password)
            user = await conn.fetchrow(
                "INSERT INTO users (email, password) VALUES ($1, $2) RETURNING id, email, is_active",
                email,
                hashed_password,
            )
            return cls(**user)
        finally:
            await conn.close()

    @classmethod
    async def get(cls: "User", user_id: int) -> "User":
        """Get a user by id."""
        conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
        try:
            user = await conn.fetchrow("SELECT id, email, is_active FROM users WHERE id = $1", user_id)
            return cls(**user)
        finally:
            await conn.close()

    @classmethod
    async def exists(cls: "User", email: str) -> bool:
        """Check if a user exists by email."""
        conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
        try:
            user = await conn.fetchval("SELECT id FROM users WHERE email = $1", email)
            return bool(user)
        finally:
            await conn.close()

    @classmethod
    async def get_by_email(cls: "User", email: str, password: str) -> "User":
        """Get a user by email if the password is correct."""
        if not await cls.exists(email):
            msg = "User not found"
            raise ValueError(msg)
        conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
        try:
            user = await conn.fetchrow(
                "SELECT id, email, is_active FROM users WHERE email = $1 and password = crypt($2, password)",
                email,
                password,
            )
            if not user:
                msg = "Incorrect password"
                raise ValueError(msg)
            return cls(**user)
        finally:
            await conn.close()

    async def activate(self: "User") -> "User":
        """Activate the user."""
        conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
        try:
            await conn.execute("BEGIN")
            await conn.execute("UPDATE users SET is_active = TRUE WHERE id = $1", self.id)
            await conn.execute("COMMIT")
            self.is_active = True
            return self
        finally:
            await conn.close()
