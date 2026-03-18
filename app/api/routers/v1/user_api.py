"""User API."""

from typing import Annotated

from colorlog import getLogger
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.api.dependencies import get_auth_service
from app.api.schemas.auth import ActivationRequest, RegistrationRequest
from app.domain.exceptions import DomainError
from app.models.user import User
from app.services.auth_service import AuthService

router = APIRouter()

logger = getLogger(__name__)

security = HTTPBasic()


@router.post("/register/")
async def register_user(
    payload: RegistrationRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Register a new user."""
    try:
        return await auth_service.register(payload.email, payload.password)
    except DomainError:
        raise
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
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Activate a user."""
    try:
        return await auth_service.activate(
            email=credentials.username,
            password=credentials.password,
            token=payload.token,
        )
    except DomainError:
        raise
    except Exception as e:
        logger.exception("Error activating user", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error activating user",
        ) from e
