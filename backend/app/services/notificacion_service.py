"""Notificaciones: fila en `NOTIFICACION` + encolado en ARQ (RF-22, RNF-11).

El envío **nunca** aborta la operación de negocio: si Redis o SMTP fallan, la
fila queda en `PENDIENTE`/`FALLIDA` con el motivo, y la transacción principal ya
está confirmada.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.timezone import now_utc
from app.db.models.enums import EstadoNotificacion, TipoNotificacion
from app.db.models.notificacion import Notificacion
from app.db.models.usuario import Usuario

logger = structlog.get_logger(__name__)
settings = get_settings()

ENLACE_VERIFICACION = "verificar-email"
ENLACE_RECUPERACION = "restablecer-password"


def crear(
    session: AsyncSession,
    *,
    usuario: Usuario,
    tipo: TipoNotificacion,
    id_turno: UUID | None = None,
    subtipo: str | None = None,
) -> Notificacion:
    """Agrega la fila (sin commit) para que caiga con la transacción que la motiva."""
    notificacion = Notificacion(
        id_usuario_destinatario=usuario.id_usuario,
        tipo=tipo,
        id_turno=id_turno,
        subtipo=subtipo,
        estado=EstadoNotificacion.PENDIENTE,
        fecha_programada_envio=now_utc(),
    )
    session.add(notificacion)
    return notificacion


def _pie() -> str:
    return (
        "\n\nSi no reconocés esta operación, ignorá este mensaje: no se hizo ningún "
        "cambio en tu cuenta.\n\n"
        f"Sistema de Turnos Médicos — {settings.frontend_url}"
    )


def saludo(usuario: Usuario) -> str:
    return f"Hola {usuario.nombre}:"


def cuerpo_verificacion(usuario: Usuario, token: str) -> tuple[str, str]:
    """Asunto y cuerpo del correo de verificación (RF-20, CU-11)."""
    enlace = f"{settings.frontend_url}/{ENLACE_VERIFICACION}?token={token}"
    asunto = "Verificá tu correo para reservar turnos"
    cuerpo = (
        f"{saludo(usuario)}\n\n"
        "Gracias por registrarte. Para poder reservar turnos necesitás verificar "
        "tu correo electrónico.\n\n"
        f"Confirmá tu correo acá: {enlace}\n\n"
        "El enlace es de un solo uso y vence en 24 horas."
        f"{_pie()}"
    )
    return asunto, cuerpo


def cuerpo_recuperacion(usuario: Usuario, token: str) -> tuple[str, str]:
    """Asunto y cuerpo del correo de restablecimiento (RF-21, CU-12)."""
    enlace = f"{settings.frontend_url}/{ENLACE_RECUPERACION}?token={token}"
    asunto = "Restablecer tu contraseña"
    cuerpo = (
        f"{saludo(usuario)}\n\n"
        "Recibimos una solicitud para restablecer tu contraseña.\n\n"
        f"Elegí una nueva contraseña acá: {enlace}\n\n"
        "El enlace es de un solo uso y vence en 1 hora."
        f"{_pie()}"
    )
    return asunto, cuerpo


async def despachar(
    notificacion: Notificacion, *, destinatario: str, asunto: str, cuerpo: str
) -> bool:
    """Encola el envío. Devuelve `False` si no se pudo, sin lanzar excepción."""
    pool = None
    try:
        pool = await create_pool(RedisSettings.from_dsn(settings.arq_redis_url))
        await pool.enqueue_job(
            "enviar_email",
            str(notificacion.id_notificacion),
            destinatario,
            asunto,
            cuerpo,
        )
        return True
    except Exception:
        logger.exception(
            "notificacion_no_encolada", id_notificacion=str(notificacion.id_notificacion)
        )
        return False
    finally:
        if pool is not None:
            await pool.aclose()
