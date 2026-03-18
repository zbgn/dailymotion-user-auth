"""Centralized application settings."""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    """Application configuration loaded from environment variables."""

    database_url: str | None
    smtp_server: str | None
    smtp_port: int | None
    tz: str | None


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    smtp_port_raw = os.environ.get("SMTP_PORT")
    smtp_port = int(smtp_port_raw) if smtp_port_raw else None
    return Settings(
        database_url=os.environ.get("DATABASE_URL"),
        smtp_server=os.environ.get("SMTP_SERVER"),
        smtp_port=smtp_port,
        tz=os.environ.get("TZ"),
    )
