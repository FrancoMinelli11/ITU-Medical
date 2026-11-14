"""Dependencias compartidas: sesión, Redis y usuario autenticado."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApiError
from app.core.security import decode_access_token
from app.db.models.enums import RolUsuario
from app.db.models.usuario import Usuario
from app.db.redis import get_rate_limit_redis, get_refresh_redis
from app.db.session import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session)]
RateLimitRedisDep = Annotated[Redis, Depends(get_rate_limit_redis)]
RefreshRedisDep = Annotated[Redis, Depends(get_refresh_redis)]

# `auto_error=False` para responder siempre en RFC 7807 en lugar del 403 que
# devuelve FastAPI por defecto cuando falta el header.
_bearer = HTTPBearer(auto_error=False, description="JWT de acceso")
BearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


def _no_autenticado(detail: str = "Iniciá sesión para continuar.") -> ApiError:
    return ApiError(
        401,
        "NO_AUTENTICADO",
        "No autenticado",
        detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    session: SessionDep,
    credentials: BearerDep,
) -> Usuario:
    if credentials is None:
        raise _no_autenticado()

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise ApiError(
            401,
            "TOKEN_INVALIDO",
            "Sesión inválida",
            "El token de acceso venció o no es válido.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        ) from exc

    try:
        id_usuario = UUID(str(payload.get("sub")))
    except (TypeError, ValueError) as exc:
        raise _no_autenticado() from exc

    usuario = await session.get(Usuario, id_usuario)
    if usuario is None:
        raise _no_autenticado()

    if not usuario.habilitado:
        raise ApiError(
            403,
            "CUENTA_DESHABILITADA",
            "Cuenta deshabilitada",
            "Tu cuenta está deshabilitada. Contactá a recepción.",
        )

    return usuario


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


def require_roles(*roles: RolUsuario) -> Callable[..., Awaitable[Usuario]]:
    """Valida el rol en el servidor, no alcanza con ocultar el botón (RNF-03).

    Además exige que la contraseña ya esté actualizada (C3): las cuentas creadas
    por recepción no pueden usar ningún endpoint de negocio antes del primer
    ingreso. Los endpoints de `/auth` usan `CurrentUser` y quedan afuera.
    """

    async def _dependencia(usuario: CurrentUser) -> Usuario:
        if usuario.rol not in roles:
            raise ApiError(
                403,
                "SIN_PERMISO",
                "Sin permiso",
                "No tenés permisos para realizar esta operación.",
            )
        return await require_password_actualizada(usuario)

    return _dependencia


async def require_password_actualizada(usuario: CurrentUser) -> Usuario:
    """Bloquea todo hasta que la cuenta creada por recepción cambie el DNI.

    C3: se aplica a los endpoints de negocio, nunca a `/auth/me`, `/auth/refresh`,
    `/auth/logout`, `/auth/cambiar-password` ni `/auth/primer-ingreso`. El flag se
    lee de la fila `USUARIO` en cada request, así que no queda pegado en el JWT.
    """
    if usuario.debe_cambiar_password:
        raise ApiError(
            403,
            "CAMBIO_PASSWORD_REQUERIDO",
            "Cambio de contraseña requerido",
            "Tenés que cambiar la contraseña antes de continuar.",
        )
    return usuario
