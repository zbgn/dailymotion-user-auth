"""Integration tests for authentication API endpoints using real DB wiring."""

import os
import re
from collections.abc import Iterator
from http import HTTPStatus

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.infrastructure.settings import get_settings
from app.main import app

TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"  # noqa: S105
SMTP_DOWN_ERROR = "smtp down"


def _is_ci() -> bool:
    """Return whether tests are running in CI environment."""
    return os.getenv("CI", "").lower() == "true"


@pytest.fixture
def database_url() -> str:
    """Return configured database URL or skip when integration DB is unavailable."""
    settings = get_settings()
    if not settings.database_url:
        if _is_ci():
            pytest.fail("DATABASE_URL must be configured in CI for integration tests")
        pytest.skip(reason="DATABASE_URL is not configured for integration tests")
    return settings.database_url


@pytest.fixture(autouse=True)
def _reset_db(database_url: str) -> None:
    """Reset integration tables between tests for deterministic behavior."""
    try:
        with psycopg.connect(database_url, autocommit=True) as conn, conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE tokens, users RESTART IDENTITY")
    except psycopg.OperationalError:
        if _is_ci():
            pytest.fail("PostgreSQL must be reachable in CI for integration tests")
        pytest.skip(reason="PostgreSQL is not reachable for integration tests")


@pytest.fixture
def sent_messages(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    """Capture outgoing emails while keeping real application/service wiring."""
    messages: list[dict[str, str]] = []

    async def _capture_send(_self, *, email: str, subject: str, text: str) -> None:  # noqa: ANN001
        messages.append({"email": email, "subject": subject, "text": text})

    monkeypatch.setattr("app.infrastructure.email_client.EmailClient._send", _capture_send)
    return messages


@pytest.fixture
def api_client(database_url: str) -> Iterator[TestClient]:
    """Return API test client with app lifespan and real dependency wiring."""
    _ = database_url
    with TestClient(app) as client:
        yield client


def _extract_code_from_messages(messages: list[dict[str, str]]) -> str:
    """Extract 4-digit activation code from captured welcome email text."""
    welcome_messages = [item for item in messages if item["subject"] == "Welcome to our services!"]
    if not welcome_messages:
        msg = "No welcome email captured"
        raise AssertionError(msg)

    match = re.search(r"(\d{4})", welcome_messages[-1]["text"])
    if match is None:
        msg = "No 4-digit code found in welcome email"
        raise AssertionError(msg)

    return match.group(1)


def _expire_token(database_url: str, email: str) -> None:
    """Force latest token for the user to be expired for deterministic test behavior."""
    with psycopg.connect(database_url, autocommit=True) as conn, conn.cursor() as cursor:
        cursor.execute(
            "UPDATE tokens "
            "SET valid_until = (NOW() AT TIME ZONE 'UTC') - INTERVAL '1 second' "
            "WHERE user_id = (SELECT id FROM users WHERE email = %s)",
            (email,),
        )


def test_register_success(api_client: TestClient, sent_messages: list[dict[str, str]]) -> None:
    """Register endpoint persists a user and sends activation email."""
    response = api_client.post(
        "/api/v1/register/",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["email"] == TEST_EMAIL
    assert response.json()["is_active"] is False
    assert _extract_code_from_messages(sent_messages).isdigit()


def test_duplicate_registration(api_client: TestClient) -> None:
    """Register endpoint returns business error when email already exists."""
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


def test_activate_success(api_client: TestClient, sent_messages: list[dict[str, str]]) -> None:
    """Activate endpoint succeeds with real persisted token and Basic Auth."""
    _ = api_client.post(
        "/api/v1/register/",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    token = _extract_code_from_messages(sent_messages)

    response = api_client.post(
        "/api/v1/activate/",
        json={"token": token},
        auth=(TEST_EMAIL, TEST_PASSWORD),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["email"] == TEST_EMAIL
    assert response.json()["is_active"] is True


def test_activate_success_when_confirmation_email_fails(
    api_client: TestClient,
    sent_messages: list[dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Activate endpoint remains successful after committed state change even if email delivery fails."""
    _ = api_client.post(
        "/api/v1/register/",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    token = _extract_code_from_messages(sent_messages)

    async def _fail_only_activation_email(_self, *, email: str, subject: str, text: str) -> None:  # noqa: ANN001
        _ = email, text
        if subject == "Your account has been activated":
            raise RuntimeError(SMTP_DOWN_ERROR)

    monkeypatch.setattr("app.infrastructure.email_client.EmailClient._send", _fail_only_activation_email)

    response = api_client.post(
        "/api/v1/activate/",
        json={"token": token},
        auth=(TEST_EMAIL, TEST_PASSWORD),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["email"] == TEST_EMAIL
    assert response.json()["is_active"] is True


def test_activate_wrong_code(api_client: TestClient) -> None:
    """Activate endpoint returns invalid token when code does not match persisted token."""
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


def test_activate_expired_code(
    api_client: TestClient,
    database_url: str,
    sent_messages: list[dict[str, str]],
) -> None:
    """Activate endpoint returns expired token when persisted token is forced expired."""
    _ = api_client.post(
        "/api/v1/register/",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    token = _extract_code_from_messages(sent_messages)
    _expire_token(database_url, TEST_EMAIL)

    response = api_client.post(
        "/api/v1/activate/",
        json={"token": token},
        auth=(TEST_EMAIL, TEST_PASSWORD),
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"detail": "Expired token"}
