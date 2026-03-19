"""Centralized FastAPI exception handlers for business errors."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    ExpiredActivationCodeError,
    InvalidActivationCodeError,
    InvalidCredentialsError,
    UserAlreadyActiveError,
    UserAlreadyExistsError,
    UserNotFoundError,
)


def _error_response(status_code: int, detail: str) -> JSONResponse:
    """Return a standard API error payload."""
    return JSONResponse(status_code=status_code, content={"detail": detail})


def register_error_handlers(app: FastAPI) -> None:
    """Register business error handlers on the FastAPI app."""

    @app.exception_handler(UserAlreadyExistsError)
    async def handle_user_exists(_: Request, __: UserAlreadyExistsError) -> JSONResponse:
        return _error_response(status.HTTP_400_BAD_REQUEST, "Email already registered")

    @app.exception_handler(UserNotFoundError)
    async def handle_user_not_found(_: Request, __: UserNotFoundError) -> JSONResponse:
        return _error_response(status.HTTP_400_BAD_REQUEST, "Invalid credentials")

    @app.exception_handler(InvalidCredentialsError)
    async def handle_invalid_credentials(_: Request, __: InvalidCredentialsError) -> JSONResponse:
        return _error_response(status.HTTP_400_BAD_REQUEST, "Invalid credentials")

    @app.exception_handler(UserAlreadyActiveError)
    async def handle_user_already_active(_: Request, __: UserAlreadyActiveError) -> JSONResponse:
        return _error_response(status.HTTP_400_BAD_REQUEST, "User already active")

    @app.exception_handler(InvalidActivationCodeError)
    async def handle_invalid_activation_code(_: Request, __: InvalidActivationCodeError) -> JSONResponse:
        return _error_response(status.HTTP_400_BAD_REQUEST, "Invalid token")

    @app.exception_handler(ExpiredActivationCodeError)
    async def handle_expired_activation_code(_: Request, __: ExpiredActivationCodeError) -> JSONResponse:
        return _error_response(status.HTTP_400_BAD_REQUEST, "Expired token")

