"""Main module of the application."""

from fastapi import FastAPI

from app.api.routers.v1.health import router as health_router
from app.api.routers.v1.user_api import router as user_router

app = FastAPI(
    title="Dailymotion Auth",
    description="A simple authentication service",
    version="0.1.0",
)

app.include_router(user_router)
app.include_router(user_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
