"""Application service for authentication use cases."""

import secrets

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
from app.infrastructure.db import get_db_connection
from app.infrastructure.settings import get_settings
from app.models.user import User
from app.repositories.activation_token_repository import ActivationTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailSubject, send_email

user_repository = UserRepository()
token_repository = ActivationTokenRepository()


class AuthService:
    """Pragmatic orchestration for register/activate use cases."""

    def __init__(
        self,
        database_url: str | None = None,
        user_repository: UserRepository | None = None,
        token_repository: ActivationTokenRepository | None = None,
    ) -> None:
        """Initialize service with optional database URL override."""
        self.database_url = database_url or get_settings().database_url
        self.user_repository = user_repository or UserRepository(database_url=self.database_url)
        self.token_repository = token_repository or ActivationTokenRepository(database_url=self.database_url)

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
            cleanup_conn = await get_db_connection(self.database_url)
            try:
                async with cleanup_conn.transaction():
                    await self.token_repository.delete_for_user(user.id, conn=cleanup_conn)
                    await self.user_repository.delete_by_id(user.id, conn=cleanup_conn)
            finally:
                await cleanup_conn.close()

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
            raise EmailDeliveryFailedError from exc

        return updated_user
