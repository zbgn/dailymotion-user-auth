"""User API."""

from typing import Annotated

from colorlog import getLogger
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.api.schemas.auth import ActivationRequest, RegistrationRequest
from app.domain.exceptions import (
    ExpiredActivationCodeError,
    InvalidActivationCodeError,
    InvalidCredentialsError,
    UserAlreadyActiveError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.models.user import User
from app.services.auth_service import AuthService

router = APIRouter()

logger = getLogger(__name__)

security = HTTPBasic()
auth_service = AuthService()


@router.post("/register/")
async def register_user(payload: RegistrationRequest) -> User:
    """Register a new user."""
    try:
        return await auth_service.register(payload.email, payload.password)
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        ) from None
    except Exception as e:
        logger.exception("Error creating user", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user",
        ) from e


@router.post("/activate/")
async def activate_user(
    payload: ActivationRequest,
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
) -> User:
    """Activate a user."""
    try:
        return await auth_service.activate(
            email=credentials.username,
            password=credentials.password,
            token=payload.token,
        )
    except (UserNotFoundError, InvalidCredentialsError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except UserAlreadyActiveError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already active",
        ) from None
    except (InvalidActivationCodeError, ExpiredActivationCodeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        ) from None
    except Exception as e:
        logger.exception("Error activating user", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error activating user",
        ) from e
