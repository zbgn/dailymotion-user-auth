"""FastAPI dependency wiring for API layer."""

from typing import Annotated

from fastapi import Depends

from app.infrastructure.settings import Settings, get_settings
from app.repositories.activation_token_repository import ActivationTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


def get_app_settings() -> Settings:
    """Return application settings for dependency injection."""
    return get_settings()


def get_user_repository(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> UserRepository:
    """Provide user repository dependency."""
    return UserRepository(database_url=settings.database_url)


def get_activation_token_repository(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ActivationTokenRepository:
    """Provide activation token repository dependency."""
    return ActivationTokenRepository(database_url=settings.database_url)


def get_auth_service(
    settings: Annotated[Settings, Depends(get_app_settings)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    token_repository: Annotated[ActivationTokenRepository, Depends(get_activation_token_repository)],
) -> AuthService:
    """Provide auth service dependency."""
    return AuthService(
        database_url=settings.database_url,
        user_repository=user_repository,
        token_repository=token_repository,
    )
