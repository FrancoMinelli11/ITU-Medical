"""Tarea ARQ que envía un correo y actualiza el estado de `NOTIFICACION`.

Reintentos (RNF-11): máximo 3, con backoff 60, 300 y 900 segundos. Agotados los
intentos, la fila queda en `FALLIDA` con el último error. El fallo de envío no
toca la operación de negocio: solo esta fila.
"""

from __future__ import annotations

import asyncio
import smtplib
from uuid import UUID

import structlog
from arq import Retry

from app.core.timezone import now_utc
from app.db.models.enums import EstadoNotificacion
from app.db.models.notificacion import Notificacion
from app.db.session import SessionLocal
from app.services import email_service

logger = structlog.get_logger(__name__)

MAX_INTENTOS = 3
ESPERAS = (60, 300, 900)


async def enviar_email(
    ctx: dict[str, object],
    id_notificacion: str,
    destinatario: str,
    asunto: str,
    cuerpo: str,
) -> str:
    async with SessionLocal() as session:
        notificacion = await session.get(Notificacion, UUID(id_notificacion))
        if notificacion is None:
            logger.warning("notificacion_inexistente", id_notificacion=id_notificacion)
            return "sin_notificacion"
        if notificacion.estado is EstadoNotificacion.ENVIADA:
            # Idempotencia: un reenvío del job no vuelve a mandar el correo.
            return "ya_enviada"

        notificacion.intentos += 1
        try:
            await asyncio.to_thread(email_service.enviar, destinatario, asunto, cuerpo)
        except (OSError, smtplib.SMTPException) as exc:
            notificacion.ultimo_error = f"{type(exc).__name__}: {exc}"[:500]
            if notificacion.intentos >= MAX_INTENTOS:
                notificacion.estado = EstadoNotificacion.FALLIDA
                await session.commit()
                logger.error(
                    "email_fallido_definitivo",
                    id_notificacion=id_notificacion,
                    intentos=notificacion.intentos,
                )
                return "fallida"
            notificacion.estado = EstadoNotificacion.PENDIENTE
            await session.commit()
            espera = ESPERAS[min(notificacion.intentos - 1, len(ESPERAS) - 1)]
            logger.warning(
                "email_reintentara",
                id_notificacion=id_notificacion,
                intentos=notificacion.intentos,
                espera=espera,
            )
            raise Retry(defer=espera) from exc

        notificacion.estado = EstadoNotificacion.ENVIADA
        notificacion.fecha_envio = now_utc()
        notificacion.ultimo_error = None
        await session.commit()
        logger.info("email_enviado", id_notificacion=id_notificacion)
        return "enviada"
