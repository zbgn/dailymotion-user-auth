"""User API."""

import random
from typing import Annotated

from colorlog import getLogger
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.api.schemas.auth import ActivationRequest, RegistrationRequest
from app.models.user import User
from app.repositories.activation_token_repository import ActivationTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailSubject, send_email

router = APIRouter()

logger = getLogger(__name__)

security = HTTPBasic()
user_repository = UserRepository()
token_repository = ActivationTokenRepository()


@router.post("/register/")
async def register_user(payload: RegistrationRequest) -> User:
    """Register a new user."""
    email = payload.email
    password = payload.password
    user_in_db = await user_repository.exists(email)
    if user_in_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    try:
        user = await user_repository.create(email=email, password=password)
        random_code = "".join([str(random.randint(0, 9)) for _ in range(4)])  # noqa: S311
        token = await token_repository.create(code=random_code, user_id=user.id)
        await send_email(email=user.email, subject=EmailSubject.WELCOME, token=token.code)
    except Exception as e:
        logger.exception("Error creating user", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user",
        ) from e
    return user


@router.post("/activate/")
async def activate_user(
    payload: ActivationRequest,
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
) -> User:
    """Activate a user."""
    token = payload.token
    try:
        user = await user_repository.get_by_email(credentials.username, credentials.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already active",
        )
    latetest_token = await token_repository.get_by_user_email(credentials.username)
    if not latetest_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )
    if latetest_token.code == token and latetest_token.is_valid:
        try:
            updated_user = await user_repository.activate(user.id)
            await send_email(credentials.username, EmailSubject.ACTIVATED)
        except Exception as e:
            logger.exception("Error activating user", exc_info=e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error activating user",
            ) from e
        else:
            return updated_user
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid token",
    )
