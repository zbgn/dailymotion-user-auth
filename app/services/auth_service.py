"""Application service for authentication use cases."""

import logging
import secrets
from typing import Protocol

import asyncpg

from app.domain.exceptions import (
    EmailDeliveryFailedError,
    ExpiredActivationCodeError,
    InvalidActivationCodeError,
    InvalidCredentialsError,
    UserAlreadyActiveError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.infrastructure.db import ManagedConnection, get_db_connection
from app.infrastructure.settings import get_settings
from app.models.token import Token
from app.models.user import User
from app.repositories.activation_token_repository import ActivationTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailSubject, send_email

logger = logging.getLogger(__name__)


class UserRepositoryPort(Protocol):
    """Protocol for user repository operations consumed by AuthService."""

    async def exists(self, email: str, conn: ManagedConnection | None = None) -> bool:
        """Return whether a user exists by email."""

    async def create(self, email: str, password: str, conn: ManagedConnection | None = None) -> User:
        """Create and return a user."""

    async def get_by_email(self, email: str, password: str, conn: ManagedConnection | None = None) -> User:
        """Return a user by credentials."""

    async def activate(self, user_id: int, conn: ManagedConnection | None = None) -> User:
        """Activate and return a user."""

    async def delete_by_id(self, user_id: int, conn: ManagedConnection | None = None) -> None:
        """Delete a user by id."""


class ActivationTokenRepositoryPort(Protocol):
    """Protocol for token repository operations consumed by AuthService."""

    async def create(self, code: str, user_id: int, conn: ManagedConnection | None = None) -> Token:
        """Create and return a token."""

    async def delete_for_user(self, user_id: int, conn: ManagedConnection | None = None) -> None:
        """Delete all tokens for a user."""

    async def get_by_user_email_and_code(
        self,
        user_email: str,
        code: str,
        conn: ManagedConnection | None = None,
    ) -> Token | None:
        """Return token matching user and code."""

    async def get_valid_by_user_email_and_code(
        self,
        user_email: str,
        code: str,
        conn: ManagedConnection | None = None,
    ) -> Token | None:
        """Return non-expired token matching user and code."""

    async def invalidate_for_user(self, user_id: int, conn: ManagedConnection | None = None) -> None:
        """Invalidate all tokens for a user."""


class AuthService:
    """Pragmatic orchestration for register/activate use cases."""

    def __init__(
        self,
        database_url: str | None = None,
        user_repository: UserRepositoryPort | None = None,
        token_repository: ActivationTokenRepositoryPort | None = None,
    ) -> None:
        """Initialize service with optional database URL override."""
        self.database_url = database_url or get_settings().database_url
        if user_repository is None:
            self.user_repository: UserRepositoryPort = UserRepository(database_url=self.database_url)
        else:
            self.user_repository = user_repository

        if token_repository is None:
            self.token_repository: ActivationTokenRepositoryPort = ActivationTokenRepository(
                database_url=self.database_url,
            )
        else:
            self.token_repository = token_repository

    async def register(self, email: str, password: str) -> User:
        """Register a user and send an activation code by email."""
        conn = await get_db_connection(self.database_url)
        try:
            async with conn.transaction():
                if await self.user_repository.exists(email, conn=conn):
                    raise UserAlreadyExistsError

                try:
                    user = await self.user_repository.create(email=email, password=password, conn=conn)
                except asyncpg.UniqueViolationError as exc:
                    raise UserAlreadyExistsError from exc

                code = f"{secrets.randbelow(10_000):04d}"
                token = await self.token_repository.create(code=code, user_id=user.id, conn=conn)
        finally:
            await conn.close()

        try:
            await send_email(email=user.email, subject=EmailSubject.WELCOME, token=token.code)
        except Exception as exc:
            raise EmailDeliveryFailedError from exc

        return user

    async def activate(self, email: str, password: str, token: str) -> User:
        """Activate a user account with Basic Auth identity and activation code."""
        conn = await get_db_connection(self.database_url)
        try:
            async with conn.transaction():
                try:
                    user = await self.user_repository.get_by_email(email, password, conn=conn)
                except ValueError as exc:
                    if str(exc) == "User not found":
                        raise UserNotFoundError from exc
                    raise InvalidCredentialsError from exc

                if user.is_active:
                    raise UserAlreadyActiveError

                token_match = await self.token_repository.get_by_user_email_and_code(email, token, conn=conn)
                if token_match is None:
                    raise InvalidActivationCodeError

                valid_token = await self.token_repository.get_valid_by_user_email_and_code(email, token, conn=conn)
                if valid_token is None:
                    raise ExpiredActivationCodeError

                updated_user = await self.user_repository.activate(user.id, conn=conn)
                await self.token_repository.invalidate_for_user(user.id, conn=conn)
        finally:
            await conn.close()

        try:
            await send_email(email, EmailSubject.ACTIVATED)
        except Exception as exc:
            logger.exception("Activation confirmation email delivery failed for %s", email, exc_info=exc)

        return updated_user
