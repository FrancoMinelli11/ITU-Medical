"""Endpoints de recepción: llegadas, sala de espera y ausencias (RF-11, RF-12, RF-15)."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import SessionDep, require_roles
from app.db.models.enums import RolUsuario
from app.db.models.usuario import Usuario
from app.schemas.recepcion import CierreJornadaResponse, TurnoEnEsperaResponse
from app.schemas.turno import TurnoResponse
from app.services import llegada_service

router = APIRouter()

StaffDep = Annotated[
    Usuario,
    Depends(require_roles(RolUsuario.RECEPCIONISTA, RolUsuario.ADMINISTRADOR)),
]
StaffOMedicoDep = Annotated[
    Usuario,
    Depends(
        require_roles(
            RolUsuario.RECEPCIONISTA,
            RolUsuario.ADMINISTRADOR,
            RolUsuario.MEDICO,
        )
    ),
]


@router.post(
    "/turnos/{id_turno}/llegada",
    response_model=TurnoResponse,
    summary="Registrar la llegada del paciente para un turno",
)
async def registrar_llegada(
    id_turno: UUID,
    session: SessionDep,
    staff: StaffDep,
    request: Request,
) -> TurnoResponse:
    return await llegada_service.registrar_llegada(
        session,
        id_turno=id_turno,
        usuario_staff=staff,
        request=request,
    )


@router.get(
    "/sala-espera",
    response_model=list[TurnoEnEsperaResponse],
    summary="Consultar sala de espera ordenada por prioridad de atención (RF-12)",
)
async def obtener_sala_espera(
    session: SessionDep,
    _: StaffOMedicoDep,
    id_medico: Annotated[UUID | None, Query(description="Filtrar por médico")] = None,
    fecha: Annotated[date | None, Query(description="Fecha de consulta (por defecto hoy)")] = None,
) -> list[TurnoEnEsperaResponse]:
    return await llegada_service.obtener_sala_espera(
        session,
        id_medico=id_medico,
        fecha=fecha,
    )


@router.post(
    "/turnos/{id_turno}/ausente",
    response_model=TurnoResponse,
    summary="Registrar individualmente la inasistencia de un paciente",
)
async def registrar_ausencia_individual(
    id_turno: UUID,
    session: SessionDep,
    staff: StaffDep,
    request: Request,
) -> TurnoResponse:
    return await llegada_service.registrar_ausencia_individual(
        session,
        id_turno=id_turno,
        usuario_staff=staff,
        request=request,
    )


@router.post(
    "/cierre-jornada",
    response_model=CierreJornadaResponse,
    summary="Cierre de jornada: marcar ausencias de turnos no asistidos",
)
async def cerrar_jornada(
    session: SessionDep,
    staff: StaffDep,
    request: Request,
    fecha: Annotated[date | None, Query(description="Fecha a cerrar (por defecto hoy)")] = None,
) -> CierreJornadaResponse:
    return await llegada_service.cerrar_jornada_ausencias(
        session,
        usuario_staff=staff,
        fecha=fecha,
        request=request,
    )
