"""Infrastructure email client for third-party SMTP transport."""

import smtplib
from contextlib import suppress
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from colorlog import getLogger

from app.infrastructure.settings import Settings, get_settings

logger = getLogger(__name__)


class EmailClient:
    """SMTP client wrapper representing an external email provider."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize client with optional settings override."""
        self._settings = settings or get_settings()

    async def send_activation_email(self, email: str, token: str) -> None:
        """Send account activation code email."""
        await self._send(
            email=email,
            subject="Welcome to our services!",
            text=f"Your authentication code is {token}",
        )

    async def send_account_activated_email(self, email: str) -> None:
        """Send account activated confirmation email."""
        await self._send(
            email=email,
            subject="Your account has been activated",
            text="Congratulations! Your account has been activated",
        )

    async def _send(self, *, email: str, subject: str, text: str) -> None:
        """Send email through SMTP transport."""
        server = None
        try:
            server = smtplib.SMTP(self._settings.smtp_server, self._settings.smtp_port)
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = "dailymotion@auth.dev"
            msg["To"] = email

            part1 = MIMEText(text, "plain")
            part2 = MIMEText(text, "html")
            msg.attach(part1)
            msg.attach(part2)

            server.sendmail("dailymotion@auth.dev", email, msg.as_string())
        except (smtplib.SMTPException, OSError) as exc:
            logger.exception("Error sending email", exc_info=exc)
            raise
        finally:
            if server is not None:
                with suppress(smtplib.SMTPException, OSError):
                    server.quit()
