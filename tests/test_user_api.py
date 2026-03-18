"""Test the user API endpoints."""

import asyncio
import datetime
from http import HTTPStatus

import pytest
from colorlog import getLogger
from fastapi.testclient import TestClient

from app.main import app
from app.models.token import Token
from app.models.user import User

client = TestClient(app)


TOKEN_LENGTH = 4


@pytest.fixture
def mock_user(request, monkeypatch) -> None:  # noqa: ANN001
    """Mock the user repository."""
    defined_email = request.param.get("email")
    defined_password = request.param.get("password")
    defined_exist = request.param.get("exist", False)

    class MockUserRepository:
        async def create(
            self: "MockUserRepository",
            email: str,
            password: str,
            conn=None,  # noqa: ANN001
        ) -> None:
            _ = email, password, conn
            if defined_email:
                return User(id=1, email=defined_email, password=defined_password, is_active=False)
            return None

        async def get_by_email(
            self: "MockUserRepository",
            email: str,
            password: str,
            conn=None,  # noqa: ANN001
        ) -> None:
            _ = email, password, conn
            return User(id=1, email=email, is_active=False)

        async def exists(self: "MockUserRepository", email: str, conn=None) -> None:  # noqa: ANN001
            _ = email, conn
            return defined_exist

        async def activate(self: "MockUserRepository", user_id: int, conn=None) -> None:  # noqa: ANN001
            _ = user_id, conn
            return User(id=1, email=defined_email, is_active=True)

    monkeypatch.setattr("app.services.auth_service.user_repository", MockUserRepository())
    return {"email": defined_email, "password": defined_password}


@pytest.fixture
def _mock_token(monkeypatch) -> None:  # noqa: ANN001
    """Mock the token repository."""

    class MockTokenRepository:
        token_code: str

        async def create(self: "MockTokenRepository", code: str, user_id: int, conn=None) -> None:  # noqa: ANN001
            _ = conn
            self.token_code = code
            valid_until = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=1)
            return Token(id=1, code=code, user_id=user_id, valid_until=valid_until)

        async def get_by_user_email(self: "MockTokenRepository", email: str, conn=None) -> None:  # noqa: ANN001
            _ = email, conn
            valid_until = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=1)
            return Token(id=1, code=self.token_code, user_id=1, valid_until=valid_until)

        async def invalidate_for_user(self: "MockTokenRepository", user_id: int, conn=None) -> None:  # noqa: ANN001
            _ = user_id, conn

    monkeypatch.setattr("app.services.auth_service.token_repository", MockTokenRepository())


@pytest.fixture
def _mock_email_service(monkeypatch) -> None:  # noqa: ANN001
    """Mock the email service."""

    async def send_email(email: str, subject: str, **kwargs: dict) -> None:
        token = kwargs.get("token")
        logger = getLogger("mocked_email_service")
        logger.setLevel("INFO")
        logger.info("token: %s", token)
        if token:
            logger.info("Sending email to %s with subject %s and token %s", email, subject, token)
        else:
            logger.info("Sending email to %s with subject %s", email, subject)

    monkeypatch.setattr("app.services.auth_service.send_email", send_email)


@pytest.fixture
def _mock_db(monkeypatch) -> None:  # noqa: ANN001, C901
    """Mock the database connection."""
    connect_future = asyncio.Future()

    class TransactionContext:
        async def __aenter__(self: "TransactionContext") -> None:
            return None

        async def __aexit__(self: "TransactionContext", exc_type, exc, tb) -> bool:  # noqa: ANN001
            _ = exc_type, exc, tb
            return False

    class ConnectResult:
        async def execute(self: "ConnectResult", _query, *_args) -> None:  # noqa: ANN001, ANN002
            return None

        async def fetchrow(self: "ConnectResult", query: str, *_args) -> dict | None:  # noqa: ANN002
            email = _args[0] if "@" in _args[0] else ""
            token = _args[0] if len(_args[0]) == TOKEN_LENGTH and str(_args[0]).isdigit() else ""
            if "INSERT INTO users" in query:
                return {"id": 1, "email": email, "is_active": False}
            if "INSERT INTO tokens" in query:
                return {"id": 1, "code": token, "user_id": 1, "valid_until": "2025-01-01T00:00:00Z"}
            if "SELECT * FROM tokens" in query:
                return {"id": 1, "code": token, "user_id": 1, "valid_until": "2025-01-01T00:00:00Z"}
            if "SELECT * FROM users" in query:
                return {"id": 1, "email": email, "is_active": False}
            if "UPDATE users SET is_active" in query:
                return None
            return None

        async def close(self: "ConnectResult") -> None:
            return None

        def transaction(self: "ConnectResult") -> TransactionContext:
            return TransactionContext()

    connect_result = ConnectResult()
    connect_future.set_result(connect_result)
    monkeypatch.setattr("asyncpg.connect", lambda _dsn: connect_future)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mock_user", "status_code", "error_msg"),
    [
        ({"email": "test@example.com", "password": "password123"}, HTTPStatus.OK, None),
        (
            {"email": "test@example.com", "password": "password123", "exist": True},
            HTTPStatus.BAD_REQUEST,
            "Email already registered",
        ),
    ],
    indirect=["mock_user"],
)
@pytest.mark.usefixtures("_mock_db", "_mock_token", "_mock_email_service")
async def test_register_user(mock_user, status_code, error_msg) -> None:  # noqa: ANN001
    """Test the user registration endpoint."""
    email = mock_user.get("email")
    password = mock_user.get("password")
    response = client.post("/register/", json={"email": email, "password": password})
    assert response.status_code == status_code
    if status_code == HTTPStatus.OK:
        assert response.json()["email"] == email
    else:
        assert response.json()["detail"] == error_msg


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mock_user"),
    [
        ({"email": "test@example.com", "password": "password123", "get_count": 1}),
    ],
    indirect=["mock_user"],
)
@pytest.mark.usefixtures("_mock_db", "_mock_token", "_mock_email_service")
async def test_activate_user(mock_user, caplog) -> None:  # noqa: ANN001
    """Test the user activation endpoint."""
    email = mock_user.get("email")
    password = mock_user.get("password")
    client.post("/register/", json={"email": email, "password": password})
    info_log_msg = [
        log.getMessage() for log in caplog.records if log.levelname == "INFO" and log.name == "mocked_email_service"
    ]
    getLogger("test_activate_user").setLevel("INFO")
    getLogger("test_activate_user").info(info_log_msg)
    token = info_log_msg[0].split()[-1]
    response = client.post("/activate/", json={"token": token}, auth=(email, password))
    assert response.status_code == HTTPStatus.OK
    assert response.json()["email"] == email
    assert response.json()["is_active"] is True
