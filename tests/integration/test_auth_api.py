"""Integration tests for authentication API endpoints."""

from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_auth_service
from app.domain.exceptions import (
    ExpiredActivationCodeError,
    InvalidActivationCodeError,
    InvalidCredentialsError,
    UserAlreadyActiveError,
    UserAlreadyExistsError,
)
from app.main import app
from app.models.user import User

TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"  # noqa: S105
VALID_CODE = "1234"
EXPIRED_CODE = "0000"


class InMemoryAuthService:
    """Deterministic in-memory auth service for API integration tests."""

    def __init__(self) -> None:
        """Initialize in-memory users and activation codes."""
        self._users: dict[str, dict[str, object]] = {}

    async def register(self, email: str, password: str) -> User:
        """Register a user or raise when email already exists."""
        if email in self._users:
            raise UserAlreadyExistsError

        self._users[email] = {
            "password": password,
            "is_active": False,
            "code": VALID_CODE,
            "expired_codes": {EXPIRED_CODE},
        }
        return User(id=1, email=email, is_active=False)

    async def activate(self, email: str, password: str, token: str) -> User:
        """Activate a user with deterministic credential/token checks."""
        user_state = self._users.get(email)
        if user_state is None or user_state["password"] != password:
            raise InvalidCredentialsError

        if user_state["is_active"]:
            raise UserAlreadyActiveError

        if token in user_state["expired_codes"]:
            raise ExpiredActivationCodeError

        if token != user_state["code"]:
            raise InvalidActivationCodeError

        user_state["is_active"] = True
        user_state["code"] = None
        return User(id=1, email=email, is_active=True)


@pytest.fixture(autouse=True)
def _clear_dependency_overrides() -> None:
    """Clear dependency overrides before and after each test."""
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def api_client() -> TestClient:
    """Return an API test client with deterministic auth service override."""
    fake_auth_service = InMemoryAuthService()

    def _override_auth_service() -> InMemoryAuthService:
        return fake_auth_service

    app.dependency_overrides[get_auth_service] = _override_auth_service
    return TestClient(app)


def test_register_success(api_client: TestClient) -> None:
    """Register endpoint returns created user for a new email."""
    response = api_client.post(
        "/api/v1/register/",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"id": 1, "email": TEST_EMAIL, "is_active": False}


def test_duplicate_registration(api_client: TestClient) -> None:
    """Register endpoint returns stable business error on duplicate email."""
    _ = api_client.post(
        "/api/v1/register/",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )

    response = api_client.post(
        "/api/v1/register/",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"detail": "Email already registered"}


def test_activate_success(api_client: TestClient) -> None:
    """Activate endpoint succeeds with valid Basic Auth and activation code."""
    _ = api_client.post(
        "/api/v1/register/",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )

    response = api_client.post(
        "/api/v1/activate/",
        json={"token": VALID_CODE},
        auth=(TEST_EMAIL, TEST_PASSWORD),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"id": 1, "email": TEST_EMAIL, "is_active": True}


def test_activate_wrong_code(api_client: TestClient) -> None:
    """Activate endpoint returns stable invalid-token error for wrong code."""
    _ = api_client.post(
        "/api/v1/register/",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )

    response = api_client.post(
        "/api/v1/activate/",
        json={"token": "9999"},
        auth=(TEST_EMAIL, TEST_PASSWORD),
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"detail": "Invalid token"}


def test_activate_expired_code(api_client: TestClient) -> None:
    """Activate endpoint returns stable expired-token error for expired code."""
    _ = api_client.post(
        "/api/v1/register/",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )

    response = api_client.post(
        "/api/v1/activate/",
        json={"token": EXPIRED_CODE},
        auth=(TEST_EMAIL, TEST_PASSWORD),
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"detail": "Expired token"}


def test_activate_invalid_basic_auth(api_client: TestClient) -> None:
    """Activate endpoint returns stable credential error for wrong Basic Auth."""
    _ = api_client.post(
        "/api/v1/register/",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )

    response = api_client.post(
        "/api/v1/activate/",
        json={"token": VALID_CODE},
        auth=(TEST_EMAIL, "wrong-password"),
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"detail": "Invalid credentials"}
