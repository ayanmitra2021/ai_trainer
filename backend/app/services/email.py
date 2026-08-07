"""Email delivery service — Phase 7.6.

Wraps aiosmtplib for async email sending. Config via environment variables:
  SMTP_HOST     — required; if unset, delivery is skipped silently
  SMTP_PORT     — default 587
  SMTP_FROM     — sender address
  SMTP_USER     — optional; used for AUTH LOGIN
  SMTP_PASSWORD — optional; used with SMTP_USER

Email failures are logged but do not raise — callers must not rely on
email delivery for correctness.
"""

from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)


async def send_nudge_emails(
    subject: str,
    body: str,
    recipients: list[dict[str, Any]],
) -> int:
    """Send nudge emails to a list of recipients.

    Returns the count of successfully sent emails.
    Logs a warning and returns 0 if SMTP_HOST is not configured.
    """
    import os

    smtp_host = os.getenv("SMTP_HOST", "")
    if not smtp_host:
        logger.warning(
            "SMTP_HOST not configured — email delivery skipped for %d recipients",
            len(recipients),
        )
        return 0

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_from = os.getenv("SMTP_FROM", "noreply@mastery-pulse.local")
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")

    sent = 0
    try:
        import aiosmtplib

        smtp = aiosmtplib.SMTP(hostname=smtp_host, port=smtp_port, start_tls=True)
        await smtp.connect()
        if smtp_user and smtp_password:
            await smtp.login(smtp_user, smtp_password)

        for recipient in recipients:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = smtp_from
                msg["To"] = recipient["email"]

                html_body = _build_html_email(
                    subject=subject,
                    body=body,
                    recipient_name=recipient.get("name", ""),
                )
                msg.attach(MIMEText(body, "plain"))
                msg.attach(MIMEText(html_body, "html"))

                await smtp.send_message(msg)
                sent += 1
            except Exception as exc:
                logger.warning(
                    "Failed to send email to %s: %s",
                    recipient.get("email"),
                    exc,
                )

        await smtp.quit()
    except Exception as exc:
        logger.warning("SMTP connection failed: %s", exc)

    return sent


def _build_html_email(subject: str, body: str, recipient_name: str) -> str:
    """Build a clean single-column HTML email."""
    safe_body = body.replace("\n", "<br>")
    safe_name = recipient_name.replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{subject}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
             max-width: 600px; margin: 0 auto; padding: 32px 16px; color: #111;">
  <div style="background: #fff; border-radius: 8px; padding: 32px; border: 1px solid #e5e7eb;">
    <p style="font-size: 14px; color: #6b7280; margin-top: 0;">Hi {safe_name},</p>
    <div style="font-size: 15px; line-height: 1.6; color: #111;">{safe_body}</div>
    <p style="font-size: 13px; color: #6b7280; margin-bottom: 0; margin-top: 24px;
              padding-top: 16px; border-top: 1px solid #e5e7eb;">
      — The Mastery Pulse Team<br>
      <span style="font-size: 12px;">You're receiving this because you're a registered
      practitioner in Mastery Pulse.</span>
    </p>
  </div>
</body>
</html>"""
