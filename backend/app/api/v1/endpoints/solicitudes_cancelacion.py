"""Endpoints de gestión y resolución de solicitudes de cancelación rápida (RF-09, P-15)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import SessionDep, require_roles
from app.db.models.enums import EstadoSolicitudCancelacion, RolUsuario
from app.db.models.usuario import Usuario
from app.schemas.cancelacion import ResolucionSolicitudRequest, SolicitudCancelacionOut
from app.services import cancelacion_service

router = APIRouter()

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


@router.get(
    "",
    response_model=list[SolicitudCancelacionOut],
    summary="Listar solicitudes de cancelación rápida",
)
async def listar_solicitudes(
    session: SessionDep,
    usuario_actual: CualquierRolDep,
    estado: Annotated[
        EstadoSolicitudCancelacion | None,
        Query(description="Filtrar por estado de la solicitud"),
    ] = None,
) -> list[SolicitudCancelacionOut]:
    return await cancelacion_service.listar_solicitudes_cancelacion(
        session,
        usuario_actual=usuario_actual,
        estado=estado,
    )


@router.post(
    "/{id_solicitud}/resolver",
    response_model=SolicitudCancelacionOut,
    summary="Aprobar o rechazar solicitud de cancelación rápida (recepción/admin)",
)
async def resolver_solicitud(
    id_solicitud: UUID,
    datos: ResolucionSolicitudRequest,
    session: SessionDep,
    staff_usuario: StaffDep,
    request: Request,
) -> SolicitudCancelacionOut:
    return await cancelacion_service.resolver_solicitud_cancelacion(
        session,
        id_solicitud=id_solicitud,
        usuario_staff=staff_usuario,
        datos=datos,
        request=request,
    )
