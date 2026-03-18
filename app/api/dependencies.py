"""FastAPI dependency wiring for API layer."""

from collections.abc import AsyncIterator
from typing import Annotated

import asyncpg
from fastapi import Depends

import app.services.auth_service as auth_service_module
from app.infrastructure.db import get_db_connection
from app.infrastructure.settings import Settings, get_settings
from app.repositories.activation_token_repository import ActivationTokenRepository
from app.repositories.user_repository import UserRepository


def get_app_settings() -> Settings:
    """Return application settings for dependency injection."""
    return get_settings()


async def get_db_connection_dependency(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AsyncIterator[asyncpg.Connection]:
    """Provide a database connection in request scope."""
    conn = await get_db_connection(settings.database_url)
    try:
        yield conn
    finally:
        await conn.close()


def get_user_repository(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> UserRepository:
    """Provide user repository dependency."""
    _ = settings
    return auth_service_module.user_repository


def get_activation_token_repository(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ActivationTokenRepository:
    """Provide activation token repository dependency."""
    _ = settings
    return auth_service_module.token_repository


def get_auth_service(
    settings: Annotated[Settings, Depends(get_app_settings)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    token_repository: Annotated[ActivationTokenRepository, Depends(get_activation_token_repository)],
) -> auth_service_module.AuthService:
    """Provide auth service dependency."""
    return auth_service_module.AuthService(
        database_url=settings.database_url,
        user_repository=user_repository,
        token_repository=token_repository,
    )
