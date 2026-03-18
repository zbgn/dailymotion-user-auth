"""Application service for authentication use cases."""

import random

from app.domain.exceptions import (
    ExpiredActivationCodeError,
    InvalidActivationCodeError,
    InvalidCredentialsError,
    UserAlreadyActiveError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.models.user import User
from app.repositories.activation_token_repository import ActivationTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailSubject, send_email

user_repository = UserRepository()
token_repository = ActivationTokenRepository()


class AuthService:
    """Pragmatic orchestration for register/activate use cases."""

    async def register(self, email: str, password: str) -> User:
        """Register a user and send an activation code by email."""
        if await user_repository.exists(email):
            raise UserAlreadyExistsError

        user = await user_repository.create(email=email, password=password)
        code = "".join([str(random.randint(0, 9)) for _ in range(4)])  # noqa: S311
        token = await token_repository.create(code=code, user_id=user.id)
        await send_email(email=user.email, subject=EmailSubject.WELCOME, token=token.code)
        return user

    async def activate(self, email: str, password: str, token: str) -> User:
        """Activate a user account with Basic Auth identity and activation code."""
        try:
            user = await user_repository.get_by_email(email, password)
        except ValueError as exc:
            if str(exc) == "User not found":
                raise UserNotFoundError from exc
            raise InvalidCredentialsError from exc

        if user.is_active:
            raise UserAlreadyActiveError

        latest_token = await token_repository.get_by_user_email(email)
        if latest_token is None or latest_token.code != token:
            raise InvalidActivationCodeError

        if not latest_token.is_valid:
            raise ExpiredActivationCodeError

        updated_user = await user_repository.activate(user.id)
        await send_email(email, EmailSubject.ACTIVATED)
        return updated_user
