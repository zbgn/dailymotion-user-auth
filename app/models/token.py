"""Token model."""

import datetime

from pydantic import BaseModel


class Token(BaseModel):
    """Token model."""

    id: int
    code: str
    user_id: int
    valid_until: datetime.datetime
