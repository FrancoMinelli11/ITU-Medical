"""Recuperación de contraseña (RF-21, RN-31, RN-32, RN-37, CU-12).

Mismo esquema que la verificación de correo: token opaco, guardado como SHA-256,
de un solo uso, expiración de 1 hora y una sola emisión vigente por usuario. La
respuesta al pedido es **siempre** la misma para no enumerar cuentas.
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
from app.core.security import (
    generate_opaque_token,
    hash_password,
    sha256_hex,
    verify_password,
)
from app.core.timezone import now_utc
from app.db.models.enums import TipoNotificacion
from app.db.models.recuperacion_password import RecuperacionPassword
from app.db.models.usuario import Usuario
from app.services import auditoria_service, notificacion_service, refresh_service
from app.services.auditoria_service import Accion

logger = structlog.get_logger(__name__)
settings = get_settings()

EXPIRACION = timedelta(hours=1)


def _token_invalido(codigo: str, detalle: str) -> ApiError:
    return ApiError(400, codigo, "Token inválido", detalle)


async def _generar(session: AsyncSession, usuario: Usuario) -> str:
    """Invalida el token vigente anterior (RN-32) y devuelve el token plano."""
    await session.execute(
        update(RecuperacionPassword)
        .where(
            RecuperacionPassword.id_usuario == usuario.id_usuario,
            RecuperacionPassword.usado.is_(False),
        )
        .values(usado=True)
    )
    token = generate_opaque_token()
    session.add(
        RecuperacionPassword(
            id_usuario=usuario.id_usuario,
            token_hash=sha256_hex(token),
            fecha_expiracion=now_utc() + EXPIRACION,
        )
    )
    return token


async def solicitar(
    session: AsyncSession, *, redis: Redis, email: str, dni: str, request: Request
) -> None:
    """RF-21: genera el token y encola el correo si el par correo + DNI existe.

    Nunca informa si el par existió: el endpoint responde lo mismo en todos los
    casos. RN-37: máximo 3 solicitudes por correo en 1 hora.
    """
    limiter = RateLimiter(
        redis,
        prefijo="recuperacion:email",
        limite=settings.rate_limit_password_reset,
    )
    clave = sha256_hex(email)
    await verificar_limites((limiter, clave))
    await limiter.registrar(clave)

    usuario = await session.scalar(
        select(Usuario).where(
            Usuario.email == email,
            Usuario.dni == dni,
            Usuario.habilitado.is_(True),
        )
    )
    if usuario is None:
        logger.info("recuperacion_sin_efecto")
        return

    token = await _generar(session, usuario)
    notificacion = notificacion_service.crear(
        session, usuario=usuario, tipo=TipoNotificacion.RECUPERACION_PASSWORD
    )
    await auditoria_service.registrar(
        session,
        accion=Accion.RECUPERACION_SOLICITADA,
        id_usuario=usuario.id_usuario,
        entidad="recuperacion_password",
        request=request,
        commit=False,
    )
    asunto, cuerpo = notificacion_service.cuerpo_recuperacion(usuario, token)
    await session.commit()
    await notificacion_service.despachar(
        notificacion, destinatario=usuario.email, asunto=asunto, cuerpo=cuerpo
    )


async def restablecer(
    session: AsyncSession, *, redis: Redis, token: str, password: str, request: Request
) -> Usuario:
    """Consume el token, cambia la contraseña y revoca todas las sesiones (C2)."""
    fila = await session.scalar(
        select(RecuperacionPassword).where(RecuperacionPassword.token_hash == sha256_hex(token))
    )
    if fila is None:
        raise _token_invalido(
            "TOKEN_INVALIDO",
            "El enlace no es válido. Pedí uno nuevo desde el inicio de sesión.",
        )
    if fila.usado:
        raise _token_invalido(
            "TOKEN_USADO", "Este enlace ya se usó. Pedí uno nuevo si no cambiaste la contraseña."
        )
    if fila.fecha_expiracion <= now_utc():
        raise _token_invalido(
            "TOKEN_EXPIRADO",
            "El enlace venció. Pedí uno nuevo desde el inicio de sesión.",
        )

    usuario = await session.get(Usuario, fila.id_usuario)
    if usuario is None or not usuario.habilitado:
        raise _token_invalido("TOKEN_INVALIDO", "El enlace no corresponde a una cuenta activa.")
    if verify_password(password, usuario.password_hash):
        raise ApiError(
            400,
            "PASSWORD_SIN_CAMBIOS",
            "Contraseña sin cambios",
            "La nueva contraseña debe ser distinta de la anterior.",
        )

    fila.usado = True
    usuario.password_hash = hash_password(password)
    usuario.debe_cambiar_password = False
    await auditoria_service.registrar(
        session,
        accion=Accion.RECUPERACION_CONSUMIDA,
        id_usuario=usuario.id_usuario,
        entidad="recuperacion_password",
        entidad_id=fila.id_recuperacion,
        request=request,
        commit=False,
    )
    await refresh_service.revocar_sesiones_usuario(redis, usuario.id_usuario)
    await session.commit()
    logger.info("password_restablecida", id_usuario=str(usuario.id_usuario))
    return usuario
