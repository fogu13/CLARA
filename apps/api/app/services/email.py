"""Plain-SMTP email sending for digests (external-review item 23).

Env-configured, stdlib-only, best-effort — the alert loop must never depend
on a mail server being up:

  CLARA_SMTP_HOST      required to enable email at all
  CLARA_SMTP_PORT      default 587
  CLARA_SMTP_USER      optional (login skipped when empty)
  CLARA_SMTP_PASSWORD  optional
  CLARA_SMTP_FROM      default = CLARA_SMTP_USER
  CLARA_SMTP_STARTTLS  default on; set 0 only for a local relay

The recipient comes from WorkspaceSettings.notification_email (already a
settings field). IONOS mailboxes (the hello@ domain) work with the defaults.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def smtp_configured() -> bool:
    return bool(os.getenv("CLARA_SMTP_HOST"))


def send_email(to: str, subject: str, body: str) -> bool:
    """Send one plain-text email. Returns True when handed to the server."""
    host = os.getenv("CLARA_SMTP_HOST")
    if not host or not to:
        return False
    port = int(os.getenv("CLARA_SMTP_PORT", "587"))
    user = os.getenv("CLARA_SMTP_USER", "")
    password = os.getenv("CLARA_SMTP_PASSWORD", "")
    sender = os.getenv("CLARA_SMTP_FROM", user or "clara@localhost")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        if (os.getenv("CLARA_SMTP_STARTTLS", "1") or "").strip().lower() not in {"0", "false", "no"}:
            smtp.starttls()
        if user:
            smtp.login(user, password)
        smtp.send_message(message)
    return True
