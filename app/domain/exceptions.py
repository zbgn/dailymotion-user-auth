"""Domain-level business exceptions."""


class DomainError(Exception):
    """Base class for business-level domain errors."""


class UserAlreadyExistsError(DomainError):
    """Raised when trying to register an email that already exists."""


class UserNotFoundError(DomainError):
    """Raised when a user cannot be found."""


class InvalidCredentialsError(DomainError):
    """Raised when user credentials are invalid."""


class UserAlreadyActiveError(DomainError):
    """Raised when trying to activate an already active user."""


class InvalidActivationCodeError(DomainError):
    """Raised when the provided activation code does not match."""


class ExpiredActivationCodeError(DomainError):
    """Raised when the activation code is expired."""
