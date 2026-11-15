"""Cambio de contraseña autenticado (RF-23, CU-13, C2).

Dos caminos comparten la misma operación de base:

- `cambiar`: sesión normal, exige la contraseña actual.
- `primer_ingreso`: cuenta creada por recepción con la contraseña temporal (DNI);
  la sesión ya está autenticada, así que solo se pide la nueva (CU-13).

En ambos casos se revocan **todas** las familias de refresh abiertas: cualquier
cambio de contraseña cierra las sesiones existentes (C2).
"""

from __future__ import annotations

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.exceptions import ApiError
from app.core.security import hash_password, verify_password
from app.db.models.usuario import Usuario
from app.services import auditoria_service, refresh_service
from app.services.auditoria_service import Accion

logger = structlog.get_logger(__name__)


def _sin_cambios() -> ApiError:
    return ApiError(
        400,
        "PASSWORD_SIN_CAMBIOS",
        "Contraseña sin cambios",
        "La nueva contraseña debe ser distinta de la anterior.",
    )


async def _aplicar(
    session: AsyncSession,
    *,
    redis: Redis,
    usuario: Usuario,
    password_nueva: str,
    accion: Accion,
    request: Request,
) -> None:
    usuario.password_hash = hash_password(password_nueva)
    usuario.debe_cambiar_password = False
    await auditoria_service.registrar(
        session,
        accion=accion,
        id_usuario=usuario.id_usuario,
        entidad="usuario",
        entidad_id=usuario.id_usuario,
        request=request,
        commit=False,
    )
    await refresh_service.revocar_sesiones_usuario(redis, usuario.id_usuario)
    await session.commit()
    logger.info("password_cambiada", id_usuario=str(usuario.id_usuario), accion=accion.value)


async def cambiar(
    session: AsyncSession,
    *,
    redis: Redis,
    usuario: Usuario,
    password_actual: str,
    password_nueva: str,
    request: Request,
) -> None:
    if not verify_password(password_actual, usuario.password_hash):
        raise ApiError(
            400,
            "PASSWORD_ACTUAL_INCORRECTA",
            "Contraseña incorrecta",
            "La contraseña actual no es correcta.",
        )
    if verify_password(password_nueva, usuario.password_hash):
        raise _sin_cambios()
    await _aplicar(
        session,
        redis=redis,
        usuario=usuario,
        password_nueva=password_nueva,
        accion=Accion.PASSWORD_CAMBIADA,
        request=request,
    )


async def primer_ingreso(
    session: AsyncSession,
    *,
    redis: Redis,
    usuario: Usuario,
    password_nueva: str,
    request: Request,
) -> None:
    if not usuario.debe_cambiar_password:
        raise ApiError(
            400,
            "PRIMER_INGRESO_YA_REALIZADO",
            "Primer ingreso completado",
            "La contraseña de esta cuenta ya fue actualizada.",
        )
    if verify_password(password_nueva, usuario.password_hash):
        raise _sin_cambios()
    await _aplicar(
        session,
        redis=redis,
        usuario=usuario,
        password_nueva=password_nueva,
        accion=Accion.PRIMER_INGRESO_COMPLETADO,
        request=request,
    )
