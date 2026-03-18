"""Health check API."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Return a basic service health response."""
    return {"status": "ok"}
