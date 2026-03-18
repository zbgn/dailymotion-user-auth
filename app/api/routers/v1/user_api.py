"""User API."""

import os
import random

import asyncpg
from colorlog import getLogger
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.api.schemas.auth import ActivationRequest, RegistrationRequest
from app.models.token import Token
from app.models.user import User
from app.services.email_service import EmailSubject, send_email

router = APIRouter()

logger = getLogger(__name__)

security = HTTPBasic()


@router.post("/register/", response_model=User)
async def register_user(payload: RegistrationRequest) -> User:
    """Register a new user."""
    email = payload.email
    password = payload.password
    user_in_db = await User.exists(email)
    if user_in_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    try:
        conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
        await conn.execute("BEGIN")
        user = await User.create(email=email, password=password)
        random_code = "".join([str(random.randint(0, 9)) for _ in range(4)])  # noqa: S311
        token = await Token.create(code=random_code, user_id=user.id)
        await send_email(email=user.email, subject=EmailSubject.WELCOME, token=token.code)
        await conn.execute("COMMIT")
    except Exception as e:
        await conn.execute("ROLLBACK")
        logger.exception("Error creating user", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user",
        ) from e
    return user


@router.get("/users/{user_id}/", response_model=User)
async def get_user(user_id: int) -> User:
    """Get a user by id."""
    user = await User.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not active",
        )


@router.post("/activate/", response_model=User)
async def activate_user(
    payload: ActivationRequest,
    credentials: HTTPBasicCredentials = Depends(security),  # noqa: B008
) -> User:
    """Activate a user."""
    token = payload.token
    try:
        user: User = await User.get_by_email(credentials.username, credentials.password)
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
    latetest_token = await Token.get_by_user_email(credentials.username)
    if latetest_token.code == token and latetest_token.is_valid:
        try:
            conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
            await conn.execute("BEGIN")
            updated_user = await user.activate()
            await send_email(credentials.username, EmailSubject.ACTIVATED)
            await conn.execute("COMMIT")
        except Exception as e:
            await conn.execute("ROLLBACK")
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
