"""Integration tests for health API endpoint."""

from http import HTTPStatus

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    """Health endpoint returns stable service status payload."""
    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}
