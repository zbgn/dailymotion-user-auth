"""User model."""

from pydantic import BaseModel


class User(BaseModel):
    """User model."""

    id: int
    email: str
    is_active: bool | None = False
