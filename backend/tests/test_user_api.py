"""Test the user API endpoints."""

import asyncio
from http import HTTPStatus

import pytest
from colorlog import getLogger
from fastapi.testclient import TestClient

from app.main import app
from app.models.token import Token
from app.models.user import User

client = TestClient(app)


TOKEN_LENGTH = 4


@pytest.fixture()
def mock_user(request, monkeypatch) -> None:  # noqa: ANN001
    """Mock the user model."""
    defined_email = request.param.get("email")
    get_count = request.param.get("get_count", 1)

    class MockUser:
        get_counter = 0
        mocked_user_logger = getLogger("mocked_user")

        @classmethod
        async def create(cls: "MockUser", email: str) -> None:
            _ = email
            if defined_email:
                return User(id=1, email=defined_email, is_active=False)
            return None

        @classmethod
        async def get_by_email(cls: "MockUser", email: str) -> None:
            _ = email
            if cls.get_counter < get_count:
                cls.get_counter += 1
                return None
            return User(id=1, email=email, is_active=False)

    monkeypatch.setattr("app.api.user_api.User", MockUser)
    return defined_email


@pytest.fixture()
def _mock_token(monkeypatch) -> None:  # noqa: ANN001
    """Mock the token model."""

    class MockToken:
        token_code: str

        @classmethod
        async def create(cls: "MockToken", code: str, user_id: int) -> None:
            cls.token_code = code
            return Token(id=1, code=code, user_id=user_id, valid_until="2025-01-01T00:00:00Z")

        @classmethod
        async def get_by_user_email(cls: "MockToken", email: str) -> None:
            _ = email
            return Token(id=1, code=cls.token_code, user_id=1, valid_until="2025-01-01T00:00:00Z")

    monkeypatch.setattr("app.api.user_api.Token", MockToken)


@pytest.fixture()
def _mock_email_service(monkeypatch) -> None:  # noqa: ANN001
    """Mock the email service."""

    async def send_email(email: str, subject: str, **kwargs: dict) -> None:
        token = kwargs.get("token")
        logger = getLogger("mocked_email_service")
        logger.setLevel("INFO")
        if token:
            logger.info("Sending email to %s with subject %s and token %s", email, subject, token)
        else:
            logger.info("Sending email to %s with subject %s", email, subject)

    monkeypatch.setattr("app.api.user_api.send_email", send_email)


@pytest.fixture()
def _mock_db(monkeypatch) -> None:  # noqa: ANN001
    """Mock the database connection."""
    connect_future = asyncio.Future()

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

    connect_result = ConnectResult()
    connect_future.set_result(connect_result)
    monkeypatch.setattr("asyncpg.connect", lambda _dsn: connect_future)


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("mock_user", "status_code", "error_msg"),
    [
        ({"email": "test@email.com"}, HTTPStatus.OK, None),
        ({"get_count": -1}, HTTPStatus.BAD_REQUEST, "Email already registered"),
    ],
    indirect=["mock_user"],
)
@pytest.mark.usefixtures("_mock_db", "_mock_token", "_mock_email_service")
async def test_register_user(mock_user, status_code, error_msg) -> None:  # noqa: ANN001
    """Test the user registration endpoint."""
    email = mock_user
    response = client.post("/register/", params={"email": email})
    assert response.status_code == status_code
    if status_code == HTTPStatus.OK:
        assert response.json()["email"] == email
    else:
        assert response.json()["detail"] == error_msg


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("mock_user"),
    [
        ({"email": "test@email.com", "get_count": 1}),
    ],
    indirect=["mock_user"],
)
@pytest.mark.usefixtures("_mock_db", "_mock_token", "_mock_email_service")
async def test_activate_user(mock_user, caplog) -> None:  # noqa: ANN001
    """Test the user activation endpoint."""
    email = mock_user
    client.post("/register/", params={"email": email})
    info_log_msg = [
        log.getMessage() for log in caplog.records if log.levelname == "INFO" and log.name == "mocked_email_service"
    ]
    getLogger("mocked_email_service").info(info_log_msg)
    token = info_log_msg[0].split()[-1]
    response = client.post("/activate/", params={"user_email": email, "token": token})
    assert response.status_code == HTTPStatus.OK
    assert response.json()["email"] == email
    assert response.json()["is_active"] is True
