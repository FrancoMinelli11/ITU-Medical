"""Endpoints de turnos: reservas web, recepción y consultas (RF-05, RF-06, RF-07, RF-25)."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import RateLimitRedisDep, SessionDep, require_roles
from app.db.models.enums import EstadoTurno, RolUsuario
from app.db.models.usuario import Usuario
from app.schemas.cancelacion import (
    CancelacionPacienteRequest,
    CancelacionRecepcionRequest,
    SolicitudCancelacionCreate,
    SolicitudCancelacionOut,
)
from app.schemas.turno import (
    ReservaTurnoRecepcionRequest,
    ReservaTurnoWebRequest,
    TurnoResponse,
    TurnosListResponse,
)
from app.services import cancelacion_service, turno_service

router = APIRouter()

PacienteDep = Annotated[Usuario, Depends(require_roles(RolUsuario.PACIENTE))]
StaffDep = Annotated[
    Usuario,
    Depends(require_roles(RolUsuario.RECEPCIONISTA, RolUsuario.ADMINISTRADOR)),
]
CualquierRolDep = Annotated[
    Usuario,
    Depends(
        require_roles(
            RolUsuario.PACIENTE,
            RolUsuario.MEDICO,
            RolUsuario.RECEPCIONISTA,
            RolUsuario.ADMINISTRADOR,
        )
    ),
]


@router.post(
    "",
    response_model=TurnoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reserva de turno realizada por el paciente (web)",
)
async def reservar_turno_web(
    datos: ReservaTurnoWebRequest,
    session: SessionDep,
    redis: RateLimitRedisDep,
    paciente_usuario: PacienteDep,
    request: Request,
) -> TurnoResponse:
    return await turno_service.reservar_web(
        session,
        redis,
        usuario_paciente=paciente_usuario,
        datos=datos,
        request=request,
    )


@router.post(
    "/recepcion",
    response_model=TurnoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reserva de turno realizada por recepción",
)
async def reservar_turno_recepcion(
    datos: ReservaTurnoRecepcionRequest,
    session: SessionDep,
    staff_usuario: StaffDep,
    request: Request,
) -> TurnoResponse:
    return await turno_service.reservar_recepcion(
        session,
        usuario_staff=staff_usuario,
        datos=datos,
        request=request,
    )


@router.get(
    "",
    response_model=TurnosListResponse,
    summary="Listar turnos con control de permisos por rol",
)
async def listar_turnos(
    session: SessionDep,
    usuario_actual: CualquierRolDep,
    fecha_desde: Annotated[date | None, Query(description="Fecha inicio")] = None,
    fecha_hasta: Annotated[date | None, Query(description="Fecha fin")] = None,
    estado: Annotated[EstadoTurno | None, Query(description="Filtrar por estado")] = None,
    id_medico: Annotated[UUID | None, Query(description="Filtrar por médico")] = None,
    id_paciente: Annotated[UUID | None, Query(description="Filtrar por paciente")] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TurnosListResponse:
    return await turno_service.listar_turnos(
        session,
        usuario_actual=usuario_actual,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        estado=estado,
        id_medico=id_medico,
        id_paciente=id_paciente,
        pagina=pagina,
        tamano_pagina=tamano_pagina,
    )


@router.get(
    "/{id_turno}",
    response_model=TurnoResponse,
    summary="Obtener detalle de un turno específico",
)
async def obtener_turno(
    id_turno: UUID,
    session: SessionDep,
    usuario_actual: CualquierRolDep,
) -> TurnoResponse:
    return await turno_service.obtener_turno(
        session,
        id_turno=id_turno,
        usuario_actual=usuario_actual,
    )


@router.post(
    "/{id_turno}/cancelar",
    response_model=TurnoResponse,
    summary="Cancelación habitual de turno por parte del paciente (>= 24 hs)",
)
async def cancelar_turno_paciente(
    id_turno: UUID,
    session: SessionDep,
    paciente_usuario: PacienteDep,
    request: Request,
    datos: CancelacionPacienteRequest | None = None,
) -> TurnoResponse:
    return await cancelacion_service.cancelar_turno_paciente(
        session,
        id_turno=id_turno,
        usuario_paciente=paciente_usuario,
        datos=datos,
        request=request,
    )


@router.post(
    "/{id_turno}/cancelar-recepcion",
    response_model=TurnoResponse,
    summary="Cancelación administrativa de turno por recepción",
)
async def cancelar_turno_recepcion(
    id_turno: UUID,
    datos: CancelacionRecepcionRequest,
    session: SessionDep,
    staff_usuario: StaffDep,
    request: Request,
) -> TurnoResponse:
    return await cancelacion_service.cancelar_turno_recepcion(
        session,
        id_turno=id_turno,
        usuario_staff=staff_usuario,
        datos=datos,
        request=request,
    )


@router.post(
    "/{id_turno}/solicitar-cancelacion",
    response_model=SolicitudCancelacionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Solicitar cancelación rápida de turno (< 24 hs)",
)
async def solicitar_cancelacion_rapida(
    id_turno: UUID,
    datos: SolicitudCancelacionCreate,
    session: SessionDep,
    paciente_usuario: PacienteDep,
    request: Request,
) -> SolicitudCancelacionOut:
    return await cancelacion_service.solicitar_cancelacion_rapida(
        session,
        id_turno=id_turno,
        usuario_paciente=paciente_usuario,
        datos=datos,
        request=request,
    )
