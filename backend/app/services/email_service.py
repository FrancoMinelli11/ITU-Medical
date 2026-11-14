"""Envío de correo por SMTP (Mailpit en desarrollo, un proveedor real en prod)."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import get_settings

settings = get_settings()


def _construir(destinatario: str, asunto: str, cuerpo: str) -> EmailMessage:
    mensaje = EmailMessage()
    mensaje["From"] = formataddr((settings.smtp_from_name, settings.smtp_from))
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo)
    return mensaje


def enviar(destinatario: str, asunto: str, cuerpo: str) -> None:
    """Bloqueante a propósito: el worker ARQ lo corre en un hilo aparte."""
    with smtplib.SMTP(
        settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
    ) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_user and settings.smtp_password:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(_construir(destinatario, asunto, cuerpo))
