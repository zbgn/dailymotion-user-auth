"""Unit tests for auth service business behavior."""

import datetime

import pytest

from app.domain.exceptions import (
    EmailDeliveryFailedError,
    ExpiredActivationCodeError,
    InvalidActivationCodeError,
    UserAlreadyActiveError,
    UserAlreadyExistsError,
)
from app.infrastructure.db import ManagedConnection
from app.models.token import Token
from app.models.user import User
from app.services.auth_service import AuthService

TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"  # noqa: S105
FIXED_VALID_UNTIL = datetime.datetime(2030, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)


class _TransactionContext:
    """Minimal async transaction context manager for tests."""

    async def __aenter__(self) -> None:
        """Enter transaction context."""
        return

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        """Exit transaction context without suppressing exceptions."""
        _ = exc_type, exc, tb
        return False


class _FakeConnection:
    """Minimal fake DB connection object used by auth service."""

    def __init__(self) -> None:
        """Initialize connection state."""
        self.closed = False

    def transaction(self) -> _TransactionContext:
        """Return a fake transaction context manager."""
        return _TransactionContext()

    async def close(self) -> None:
        """Mark connection as closed."""
        self.closed = True


class _FakeUserRepository:
    """Simple fake user repository for service unit tests."""

    def __init__(self) -> None:
        """Initialize configurable fake behavior."""
        self.exists_result = False
        self.user_for_credentials = User(id=1, email=TEST_EMAIL, is_active=False)
        self.created_user = User(id=1, email=TEST_EMAIL, is_active=False)
        self.activated_user = User(id=1, email=TEST_EMAIL, is_active=True)
        self.activate_called_with: int | None = None
        self.deleted_user_id: int | None = None
        self.exists_called = 0
        self.create_called = 0

    async def exists(self, email: str, conn=None) -> bool:  # noqa: ANN001
        """Return configured existence state."""
        _ = email, conn
        self.exists_called += 1
        return self.exists_result

    async def create(self, email: str, password: str, conn=None) -> User:  # noqa: ANN001
        """Return configured created user."""
        _ = email, password, conn
        self.create_called += 1
        return self.created_user

    async def get_by_email(self, email: str, password: str, conn=None) -> User:  # noqa: ANN001
        """Return configured credential lookup user."""
        _ = email, password, conn
        return self.user_for_credentials

    async def activate(self, user_id: int, conn=None) -> User:  # noqa: ANN001
        """Return configured activated user."""
        _ = conn
        self.activate_called_with = user_id
        return self.activated_user

    async def delete_by_id(self, user_id: int, conn=None) -> None:  # noqa: ANN001
        """Record user deletion call for compensating cleanup."""
        _ = conn
        self.deleted_user_id = user_id


class _FakeTokenRepository:
    """Simple fake token repository for service unit tests."""

    def __init__(self) -> None:
        """Initialize configurable fake token behavior."""
        self.created_token: Token | None = None
        self.match_token: Token | None = Token(
            id=1,
            code="1234",
            user_id=1,
            valid_until=FIXED_VALID_UNTIL,
        )
        self.valid_token: Token | None = Token(
            id=1,
            code="1234",
            user_id=1,
            valid_until=FIXED_VALID_UNTIL,
        )
        self.invalidated_user_id: int | None = None
        self.deleted_user_id: int | None = None

    async def create(self, code: str, user_id: int, conn: ManagedConnection | None = None) -> Token:
        """Store and return created token."""
        _ = conn
        self.created_token = Token(id=1, code=code, user_id=user_id, valid_until=FIXED_VALID_UNTIL)
        return self.created_token

    async def get_by_user_email_and_code(
        self,
        user_email: str,
        code: str,
        conn: ManagedConnection | None = None,
    ) -> Token | None:
        """Return configured match token for code lookup."""
        _ = user_email, code, conn
        return self.match_token

    async def get_valid_by_user_email_and_code(
        self,
        user_email: str,
        code: str,
        conn: ManagedConnection | None = None,
    ) -> Token | None:
        """Return configured valid token for expiration lookup."""
        _ = user_email, code, conn
        return self.valid_token

    async def invalidate_for_user(self, user_id: int, conn: ManagedConnection | None = None) -> None:
        """Record token invalidation call."""
        _ = conn
        self.invalidated_user_id = user_id

    async def delete_for_user(self, user_id: int, conn: ManagedConnection | None = None) -> None:
        """Record token deletion call for compensating cleanup."""
        _ = conn
        self.deleted_user_id = user_id


@pytest.fixture
def fake_connection(monkeypatch: pytest.MonkeyPatch) -> _FakeConnection:
    """Patch auth service DB connection dependency with a fake connection."""
    connection = _FakeConnection()

    async def _get_db_connection(_database_url: str | None = None) -> _FakeConnection:
        _ = _database_url
        return connection

    monkeypatch.setattr("app.services.auth_service.get_db_connection", _get_db_connection)
    return connection


@pytest.fixture
def email_spy(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object | None]]:
    """Patch auth service email sender and capture invocations."""
    calls: list[dict[str, object | None]] = []

    async def _send_email(email: str, subject: str, token: str | None = None) -> None:
        calls.append({"email": email, "subject": subject, "token": token})

    monkeypatch.setattr("app.services.auth_service.send_email", _send_email)
    return calls


@pytest.mark.asyncio
async def test_register_success(
    fake_connection: _FakeConnection,
    email_spy: list[dict[str, object | None]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Register succeeds, persists user/token, and sends welcome email."""
    _ = fake_connection
    monkeypatch.setattr("app.services.auth_service.secrets.randbelow", lambda _limit: 42)

    user_repo = _FakeUserRepository()
    token_repo = _FakeTokenRepository()
    service = AuthService(
        database_url="postgresql://test",
        user_repository=user_repo,
        token_repository=token_repo,
    )

    result = await service.register(TEST_EMAIL, TEST_PASSWORD)

    assert result.email == TEST_EMAIL
    assert user_repo.exists_called == 1
    assert user_repo.create_called == 1
    assert token_repo.created_token is not None
    assert token_repo.created_token.code == "0042"
    assert len(email_spy) == 1
    assert email_spy[0]["email"] == TEST_EMAIL
    assert email_spy[0]["token"] == token_repo.created_token.code


@pytest.mark.asyncio
async def test_register_duplicate_email(
    fake_connection: _FakeConnection,
    email_spy: list[dict[str, object | None]],
) -> None:
    """Register raises business error when email already exists."""
    _ = fake_connection
    user_repo = _FakeUserRepository()
    user_repo.exists_result = True
    token_repo = _FakeTokenRepository()
    service = AuthService(
        database_url="postgresql://test",
        user_repository=user_repo,
        token_repository=token_repo,
    )

    with pytest.raises(UserAlreadyExistsError):
        await service.register(TEST_EMAIL, TEST_PASSWORD)

    assert user_repo.create_called == 0
    assert token_repo.created_token is None
    assert email_spy == []


@pytest.mark.asyncio
async def test_register_email_failure_triggers_compensating_cleanup(
    fake_connection: _FakeConnection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Register raises explicit business error and compensates when email fails."""
    _ = fake_connection
    monkeypatch.setattr("app.services.auth_service.secrets.randbelow", lambda _limit: 42)
    error_msg = "smtp down"

    async def _send_email_failure(*_args, **_kwargs) -> None:  # noqa: ANN002, ANN003
        raise RuntimeError(error_msg)

    monkeypatch.setattr("app.services.auth_service.send_email", _send_email_failure)

    user_repo = _FakeUserRepository()
    token_repo = _FakeTokenRepository()
    service = AuthService(
        database_url="postgresql://test",
        user_repository=user_repo,
        token_repository=token_repo,
    )

    with pytest.raises(EmailDeliveryFailedError):
        await service.register(TEST_EMAIL, TEST_PASSWORD)

    assert token_repo.deleted_user_id == 1
    assert user_repo.deleted_user_id == 1


@pytest.mark.asyncio
async def test_activate_success(
    fake_connection: _FakeConnection,
    email_spy: list[dict[str, object | None]],
) -> None:
    """Activate succeeds and invalidates token for subsequent reuse."""
    _ = fake_connection
    user_repo = _FakeUserRepository()
    token_repo = _FakeTokenRepository()
    service = AuthService(
        database_url="postgresql://test",
        user_repository=user_repo,
        token_repository=token_repo,
    )

    result = await service.activate(TEST_EMAIL, TEST_PASSWORD, "1234")

    assert result.is_active is True
    assert user_repo.activate_called_with == 1
    assert token_repo.invalidated_user_id == 1
    assert len(email_spy) == 1
    assert email_spy[0]["email"] == TEST_EMAIL
    assert email_spy[0]["token"] is None


@pytest.mark.asyncio
async def test_activate_email_failure_is_surfaced(
    fake_connection: _FakeConnection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Activate raises explicit delivery error if confirmation email fails."""
    _ = fake_connection
    error_msg = "smtp down"

    async def _send_email_failure(*_args, **_kwargs) -> None:  # noqa: ANN002, ANN003
        raise RuntimeError(error_msg)

    monkeypatch.setattr("app.services.auth_service.send_email", _send_email_failure)

    user_repo = _FakeUserRepository()
    token_repo = _FakeTokenRepository()
    service = AuthService(
        database_url="postgresql://test",
        user_repository=user_repo,
        token_repository=token_repo,
    )

    with pytest.raises(EmailDeliveryFailedError):
        await service.activate(TEST_EMAIL, TEST_PASSWORD, "1234")

    assert user_repo.activate_called_with == 1
    assert token_repo.invalidated_user_id == 1


@pytest.mark.asyncio
async def test_activate_wrong_code(
    fake_connection: _FakeConnection,
    email_spy: list[dict[str, object | None]],
) -> None:
    """Activate raises invalid code error when no matching token exists."""
    _ = fake_connection
    user_repo = _FakeUserRepository()
    token_repo = _FakeTokenRepository()
    token_repo.match_token = None
    service = AuthService(
        database_url="postgresql://test",
        user_repository=user_repo,
        token_repository=token_repo,
    )

    with pytest.raises(InvalidActivationCodeError):
        await service.activate(TEST_EMAIL, TEST_PASSWORD, "9999")

    assert token_repo.invalidated_user_id is None
    assert email_spy == []


@pytest.mark.asyncio
async def test_activate_expired_code(
    fake_connection: _FakeConnection,
    email_spy: list[dict[str, object | None]],
) -> None:
    """Activate raises expired code error when token exists but is no longer valid."""
    _ = fake_connection
    user_repo = _FakeUserRepository()
    token_repo = _FakeTokenRepository()
    token_repo.valid_token = None
    service = AuthService(
        database_url="postgresql://test",
        user_repository=user_repo,
        token_repository=token_repo,
    )

    with pytest.raises(ExpiredActivationCodeError):
        await service.activate(TEST_EMAIL, TEST_PASSWORD, "1234")

    assert token_repo.invalidated_user_id is None
    assert email_spy == []


@pytest.mark.asyncio
async def test_activate_already_active_user(
    fake_connection: _FakeConnection,
    email_spy: list[dict[str, object | None]],
) -> None:
    """Activate raises business error when user is already active."""
    _ = fake_connection
    user_repo = _FakeUserRepository()
    user_repo.user_for_credentials = User(id=1, email=TEST_EMAIL, is_active=True)
    token_repo = _FakeTokenRepository()
    service = AuthService(
        database_url="postgresql://test",
        user_repository=user_repo,
        token_repository=token_repo,
    )

    with pytest.raises(UserAlreadyActiveError):
        await service.activate(TEST_EMAIL, TEST_PASSWORD, "1234")

    assert token_repo.invalidated_user_id is None
    assert email_spy == []
