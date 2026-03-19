"""Email service."""

import enum

from app.infrastructure.email_client import EmailClient


class EmailSubject(enum.Enum):
    """Email messages."""

    WELCOME = "Welcome to our services!"
    ACTIVATED = "Your account has been activated"


mails = {
    EmailSubject.WELCOME: "Your authentication code is {}",
    EmailSubject.ACTIVATED: "Congratulations! Your account has been activated",
}

email_client = EmailClient()


async def send_email(email: str, subject: EmailSubject, token: str | None = None) -> None:
    """
    Send an email to the user.

    Args:
    ----
        email (str): The user's email.
        subject (EmailMsg): The email subject.
        token (str | None): Activation code for welcome emails.

    """
    if subject is EmailSubject.WELCOME:
        if token is None:
            msg = "Activation token is required for welcome email"
            raise ValueError(msg)
        await email_client.send_activation_email(email=email, token=token)
        return

    if subject is EmailSubject.ACTIVATED:
        await email_client.send_account_activated_email(email=email)
