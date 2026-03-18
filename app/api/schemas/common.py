"""Common API schema models."""

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """Reusable message response payload."""

    message: str
