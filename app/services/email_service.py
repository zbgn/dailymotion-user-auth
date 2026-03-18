"""Email service."""

import enum
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from colorlog import getLogger


class EmailSubject(enum.Enum):
    """Email messages."""

    WELCOME = "Welcome to our services!"
    ACTIVATED = "Your account has been activated"


mails = {
    EmailSubject.WELCOME: "Your authentication code is {}",
    EmailSubject.ACTIVATED: "Congratulations! Your account has been activated",
}

logger = getLogger(__name__)


async def send_email(email: str, subject: EmailSubject, *_: dict, **kwargs: dict) -> None:
    """
    Send an email to the user.

    Args:
    ----
        email (str): The user's email.
        subject (EmailMsg): The email subject.
        **kwargs: Additional keyword arguments.

    """
    server = smtplib.SMTP(os.environ.get("SMTP_SERVER"), os.environ.get("SMTP_PORT"))
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject.value
        msg["From"] = "dailymotion@auth.dev"
        msg["To"] = email
        text = mails[subject].format(kwargs.get("token"))
        html = text
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        msg.attach(part1)
        msg.attach(part2)
        server.sendmail("dailymotion@auth.dev", email, msg.as_string())
    except (
        smtplib.SMTPHeloError,
        smtplib.SMTPRecipientsRefused,
        smtplib.SMTPSenderRefused,
        smtplib.SMTPNotSupportedError,
    ) as e:
        logger.exception("Error sending email", exc_info=e)
    finally:
        server.quit()
