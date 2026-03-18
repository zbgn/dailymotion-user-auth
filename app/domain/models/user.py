"""Domain model for user."""

from dataclasses import dataclass


@dataclass(slots=True)
class User:
    """Core user entity used by business logic."""

    id: int
    email: str
    is_active: bool = False
