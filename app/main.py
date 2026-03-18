"""Main module of the application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.error_handlers import register_error_handlers
from app.api.routers.v1.health import router as health_router
from app.api.routers.v1.user_api import router as user_router
from app.infrastructure.db import close_db_pool, create_db_pool
from app.infrastructure.settings import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Manage infrastructure startup/shutdown resources."""
    settings = get_settings()
    db_pool_initialized = False
    if settings.database_url:
        await create_db_pool()
        db_pool_initialized = True

    try:
        yield
    finally:
        if db_pool_initialized:
            await close_db_pool()


app = FastAPI(
    title="Dailymotion Auth",
    description="A simple authentication service",
    version="0.1.0",
    lifespan=lifespan,
)

register_error_handlers(app)

app.include_router(user_router)
app.include_router(user_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
