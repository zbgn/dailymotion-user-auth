"""Token model."""

import datetime

import pytz
from pydantic import BaseModel


class Token(BaseModel):
    """Token model."""

    id: int
    code: str
    user_id: int
    valid_until: datetime.datetime

    @property
    def is_valid(self: "Token") -> bool:
        """Check if the token is valid."""
        return self.valid_until.replace(tzinfo=None) > datetime.datetime.now(tz=pytz.utc).replace(tzinfo=None)
