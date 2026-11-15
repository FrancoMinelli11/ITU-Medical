"""Registro en `AUDITORIA` (RF-19, RNF-08).

Toda operación sensible deja una fila con quién, qué, cuándo, desde qué IP y con
qué `X-Request-ID`, para poder correlacionar con los logs de structlog.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.http import ip_de_request
from app.db.models.auditoria import Auditoria


class Accion(StrEnum):
    LOGIN_EXITOSO = "LOGIN_EXITOSO"
    LOGIN_FALLIDO = "LOGIN_FALLIDO"
    LOGOUT = "LOGOUT"
    REFRESH = "REFRESH"
    REFRESH_REUTILIZADO = "REFRESH_REUTILIZADO"
    VERIFICACION_EMAIL_ENVIADA = "VERIFICACION_EMAIL_ENVIADA"
    EMAIL_VERIFICADO = "EMAIL_VERIFICADO"
    RECUPERACION_SOLICITADA = "RECUPERACION_SOLICITADA"
    RECUPERACION_CONSUMIDA = "RECUPERACION_CONSUMIDA"
    PASSWORD_CAMBIADA = "PASSWORD_CAMBIADA"
    PRIMER_INGRESO_COMPLETADO = "PRIMER_INGRESO_COMPLETADO"
    ALTA_USUARIO_STAFF = "ALTA_USUARIO_STAFF"
    ALTA_PACIENTE_WEB = "ALTA_PACIENTE_WEB"
    ALTA_PACIENTE_RECEPCION = "ALTA_PACIENTE_RECEPCION"
    MODIFICACION_PACIENTE = "MODIFICACION_PACIENTE"
    ALTA_ESPECIALIDAD = "ALTA_ESPECIALIDAD"
    MODIFICACION_ESPECIALIDAD = "MODIFICACION_ESPECIALIDAD"
    ALTA_MEDICO = "ALTA_MEDICO"
    MODIFICACION_MEDICO = "MODIFICACION_MEDICO"
    MODIFICACION_HORARIOS_MEDICO = "MODIFICACION_HORARIOS_MEDICO"
    ALTA_BLOQUEO_AGENDA = "ALTA_BLOQUEO_AGENDA"
    BAJA_BLOQUEO_AGENDA = "BAJA_BLOQUEO_AGENDA"


async def registrar(
    session: AsyncSession,
    *,
    accion: Accion,
    id_usuario: UUID | None = None,
    entidad: str = "usuario",
    entidad_id: UUID | None = None,
    datos_antes: dict[str, Any] | None = None,
    datos_despues: dict[str, Any] | None = None,
    request: Request | None = None,
    commit: bool = True,
) -> None:
    """Agrega la fila de auditoría y, por defecto, la confirma.

    `commit=False` se usa cuando la auditoría debe caer junto con una
    transacción de negocio más grande (alta de paciente, cambio de contraseña).
    Un fallo de login no tiene transacción propia, así que confirma solo.
    """
    session.add(
        Auditoria(
            id_usuario=id_usuario,
            accion=str(accion),
            entidad=entidad,
            entidad_id=entidad_id if entidad_id is not None else id_usuario,
            datos_antes=datos_antes,
            datos_despues=datos_despues,
            ip=ip_de_request(request) if request is not None else None,
            request_id=getattr(request.state, "request_id", None) if request is not None else None,
        )
    )
    if commit:
        await session.commit()
