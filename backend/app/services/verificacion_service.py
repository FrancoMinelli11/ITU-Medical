"""Tokens de verificación de correo (RF-20, RN-31, RN-32, CU-11).

Los tokens son opacos, se guardan **hasheados** (SHA-256) y son de un solo uso.
Cada emisión invalida el token anterior del mismo usuario, así que solo hay uno
vigente a la vez. La expiración es de 24 horas.
"""

from __future__ import annotations

from datetime import timedelta

import structlog
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config import get_settings
from app.core.exceptions import ApiError
from app.core.rate_limit import RateLimiter, verificar_limites
from app.core.security import generate_opaque_token, sha256_hex
from app.core.timezone import now_utc
from app.db.models.enums import TipoNotificacion
from app.db.models.notificacion import Notificacion
from app.db.models.usuario import Usuario
from app.db.models.verificacion_email import VerificacionEmail
from app.services import auditoria_service, notificacion_service
from app.services.auditoria_service import Accion

logger = structlog.get_logger(__name__)
settings = get_settings()

EXPIRACION = timedelta(hours=24)


def _token_invalido(codigo: str, detalle: str) -> ApiError:
    return ApiError(400, codigo, "Token inválido", detalle)


async def generar(session: AsyncSession, usuario: Usuario) -> str:
    """Invalida los tokens vigentes (RN-32) y devuelve el token plano."""
    await session.execute(
        update(VerificacionEmail)
        .where(
            VerificacionEmail.id_usuario == usuario.id_usuario,
            VerificacionEmail.usado.is_(False),
        )
        .values(usado=True)
    )
    token = generate_opaque_token()
    session.add(
        VerificacionEmail(
            id_usuario=usuario.id_usuario,
            token_hash=sha256_hex(token),
            fecha_expiracion=now_utc() + EXPIRACION,
        )
    )
    return token


async def emitir(
    session: AsyncSession, *, usuario: Usuario, request: Request
) -> tuple[Notificacion, str, str]:
    """Genera el token, crea la notificación y audita. **No** hace commit."""
    token = await generar(session, usuario)
    notificacion = notificacion_service.crear(
        session, usuario=usuario, tipo=TipoNotificacion.VERIFICACION_EMAIL
    )
    await auditoria_service.registrar(
        session,
        accion=Accion.VERIFICACION_EMAIL_ENVIADA,
        id_usuario=usuario.id_usuario,
        entidad="verificacion_email",
        request=request,
        commit=False,
    )
    asunto, cuerpo = notificacion_service.cuerpo_verificacion(usuario, token)
    return notificacion, asunto, cuerpo


async def consumir(session: AsyncSession, *, token: str, request: Request) -> Usuario:
    fila = await session.scalar(
        select(VerificacionEmail).where(VerificacionEmail.token_hash == sha256_hex(token))
    )
    if fila is None:
        raise _token_invalido(
            "TOKEN_INVALIDO", "El enlace no es válido. Pedí uno nuevo desde el inicio de sesión."
        )
    if fila.usado:
        raise _token_invalido(
            "TOKEN_USADO", "Este enlace ya se usó. Pedí uno nuevo si no verificaste tu correo."
        )
    if fila.fecha_expiracion <= now_utc():
        raise _token_invalido(
            "TOKEN_EXPIRADO", "El enlace venció. Pedí uno nuevo desde el inicio de sesión."
        )

    usuario = await session.get(Usuario, fila.id_usuario)
    if usuario is None:
        raise _token_invalido("TOKEN_INVALIDO", "El enlace no corresponde a una cuenta activa.")

    fila.usado = True
    usuario.email_verificado = True
    await auditoria_service.registrar(
        session,
        accion=Accion.EMAIL_VERIFICADO,
        id_usuario=usuario.id_usuario,
        entidad="verificacion_email",
        entidad_id=fila.id_verificacion,
        request=request,
        commit=False,
    )
    await session.commit()
    return usuario


async def reenviar(session: AsyncSession, *, email: str, redis: Redis, request: Request) -> None:
    """Reenvía el correo de verificación (respuesta genérica siempre).

    RN-37: máximo 3 solicitudes por correo en 1 hora. La clave del rate limit se
    hashea para no dejar direcciones en Redis.
    """
    limiter = RateLimiter(
        redis,
        prefijo="verificacion:email",
        limite=settings.rate_limit_verification_resend,
    )
    clave = sha256_hex(email)
    await verificar_limites((limiter, clave))
    await limiter.registrar(clave)

    usuario = await session.scalar(
        select(Usuario).where(Usuario.email == email, Usuario.habilitado.is_(True))
    )
    if usuario is None or usuario.email_verificado:
        logger.info("reenvio_verificacion_sin_efecto")
        return

    notificacion, asunto, cuerpo = await emitir(session, usuario=usuario, request=request)
    await session.commit()
    await notificacion_service.despachar(
        notificacion, destinatario=usuario.email, asunto=asunto, cuerpo=cuerpo
    )
