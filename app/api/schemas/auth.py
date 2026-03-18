"""Authentication request schema models."""

from pydantic import BaseModel, Field


class RegistrationRequest(BaseModel):
    """Registration request body."""

    email: str
    password: str = Field(max_length=72)


class ActivationRequest(BaseModel):
    """Account activation request body."""

    token: str
