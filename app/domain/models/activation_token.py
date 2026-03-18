"""Domain model for account activation token."""

import datetime
from dataclasses import dataclass


@dataclass(slots=True)
class ActivationToken:
    """Core activation token entity used by business logic."""

    id: int
    code: str
    user_id: int
    valid_until: datetime.datetime

    def is_expired(self, *, now: datetime.datetime | None = None) -> bool:
        """Return True when the token is expired relative to UTC."""
        current_time = now or datetime.datetime.now(datetime.UTC)
        token_time = self.valid_until
        if token_time.tzinfo is None:
            token_time = token_time.replace(tzinfo=datetime.UTC)
        return token_time <= current_time.astimezone(datetime.UTC)
