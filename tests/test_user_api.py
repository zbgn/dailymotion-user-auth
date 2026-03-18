"""Test the user API endpoints."""

from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_auth_service
from app.domain.exceptions import UserAlreadyExistsError
from app.main import app
from app.models.user import User

client = TestClient(app)


class MockAuthService:
    """Minimal mock auth service for API dependency override tests."""

    def __init__(self, register_error: type[Exception] | None = None) -> None:
        """Configure optional registration error behavior."""
        self.register_error = register_error

    async def register(self, email: str, password: str) -> User:
        """Return a non-active user or raise a configured registration error."""
        _ = password
        if self.register_error is not None:
            raise self.register_error
        return User(id=1, email=email, is_active=False)

    async def activate(self, email: str, password: str, token: str) -> User:
        """Return an activated user for API response assertions."""
        _ = password, token
        return User(id=1, email=email, is_active=True)


@pytest.fixture(autouse=True)
def _clear_dependency_overrides() -> None:
    """Ensure dependency overrides do not leak between tests."""
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("register_error", "status_code", "error_msg"),
    [
        (None, HTTPStatus.OK, None),
        (UserAlreadyExistsError, HTTPStatus.BAD_REQUEST, "Email already registered"),
    ],
)
def test_register_user(register_error: type[Exception] | None, status_code: HTTPStatus, error_msg: str | None) -> None:
    """Test the user registration endpoint."""
    email = "test@example.com"
    password = "password123"  # noqa: S105

    def _override_auth_service() -> MockAuthService:
        return MockAuthService(register_error=register_error)

    app.dependency_overrides[get_auth_service] = _override_auth_service

    response = client.post("/api/v1/register/", json={"email": email, "password": password})

    assert response.status_code == status_code
    if status_code == HTTPStatus.OK:
        assert response.json()["email"] == email
    else:
        assert response.json()["detail"] == error_msg


def test_activate_user() -> None:
    """Test the user activation endpoint."""
    email = "test@example.com"
    password = "password123"  # noqa: S105

    def _override_auth_service() -> MockAuthService:
        return MockAuthService()

    app.dependency_overrides[get_auth_service] = _override_auth_service

    response = client.post("/api/v1/activate/", json={"token": "1234"}, auth=(email, password))

    assert response.status_code == HTTPStatus.OK
    assert response.json()["email"] == email
    assert response.json()["is_active"] is True
