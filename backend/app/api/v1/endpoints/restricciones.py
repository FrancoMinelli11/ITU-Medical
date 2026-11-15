"""Endpoints de gestión de restricciones y Usuario rojo (RF-16, RN-20..RN-22, RN-36)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import SessionDep, require_roles
from app.core.exceptions import ApiError
from app.db.models.enums import RolUsuario
from app.db.models.paciente import Paciente
from app.db.models.usuario import Usuario
from app.schemas.restriccion import (
    RestriccionCreate,
    RestriccionEstadoOut,
    RestriccionOut,
)
from app.services import restriccion_service

router = APIRouter()

StaffDep = Annotated[
    Usuario,
    Depends(require_roles(RolUsuario.RECEPCIONISTA, RolUsuario.ADMINISTRADOR)),
]
CualquierUsuarioDep = Annotated[
    Usuario,
    Depends(
        require_roles(
            RolUsuario.PACIENTE,
            RolUsuario.RECEPCIONISTA,
            RolUsuario.MEDICO,
            RolUsuario.ADMINISTRADOR,
        )
    ),
]


@router.post(
    "",
    response_model=RestriccionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Clasificar paciente como Usuario rojo (RF-16, P-24)",
)
async def clasificar_usuario_rojo(
    datos: RestriccionCreate,
    session: SessionDep,
    staff: StaffDep,
    request: Request,
) -> RestriccionOut:
    return await restriccion_service.clasificar_usuario_rojo(
        session,
        datos=datos,
        usuario_operador=staff,
        request=request,
    )


@router.post(
    "/{id_restriccion}/levantar",
    response_model=RestriccionOut,
    summary="Levantar restricción de Usuario rojo",
)
async def levantar_restriccion(
    id_restriccion: UUID,
    session: SessionDep,
    staff: StaffDep,
    request: Request,
) -> RestriccionOut:
    return await restriccion_service.levantar_restriccion(
        session,
        id_restriccion=id_restriccion,
        usuario_operador=staff,
        request=request,
    )


@router.get(
    "/paciente/{id_paciente}",
    response_model=RestriccionEstadoOut,
    summary="Consultar estado de Usuario rojo de un paciente",
)
async def obtener_estado_paciente(
    id_paciente: UUID,
    session: SessionDep,
    usuario_actual: CualquierUsuarioDep,
) -> RestriccionEstadoOut:
    if usuario_actual.rol == RolUsuario.PACIENTE:
        paciente = await session.get(Paciente, id_paciente)
        if paciente is None or paciente.id_usuario != usuario_actual.id_usuario:
            raise ApiError(
                403,
                "ACCESO_DENEGADO",
                "Permisos insuficientes",
                "No podés consultar la condición de otro paciente.",
            )

    return await restriccion_service.obtener_estado_paciente(
        session,
        id_paciente=id_paciente,
    )


@router.get(
    "",
    response_model=list[RestriccionOut],
    summary="Listar restricciones de usuarios",
)
async def listar_restricciones(
    session: SessionDep,
    _staff: StaffDep,
    solo_activas: Annotated[bool, Query()] = True,
    id_paciente: Annotated[UUID | None, Query()] = None,
) -> list[RestriccionOut]:
    return await restriccion_service.listar_restricciones(
        session,
        solo_activas=solo_activas,
        id_paciente=id_paciente,
    )
