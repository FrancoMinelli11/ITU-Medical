"""Endpoints de anotaciones médicas de seguimiento (RF-14, P-22, P-23)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import SessionDep, require_roles
from app.db.models.enums import RolUsuario
from app.db.models.usuario import Usuario
from app.schemas.nota import (
    NotaSeguimientoCreate,
    NotaSeguimientoOut,
    NotaSeguimientoUpdate,
)
from app.services import nota_service

router = APIRouter()

MedicoOAdminDep = Annotated[
    Usuario,
    Depends(require_roles(RolUsuario.MEDICO, RolUsuario.ADMINISTRADOR)),
]


@router.post(
    "",
    response_model=NotaSeguimientoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una nueva anotación médica de seguimiento (RF-14, P-22)",
)
async def crear_nota(
    datos: NotaSeguimientoCreate,
    session: SessionDep,
    medico: MedicoOAdminDep,
    request: Request,
) -> NotaSeguimientoOut:
    return await nota_service.crear_nota_seguimiento(
        session,
        datos=datos,
        usuario_medico=medico,
        request=request,
    )


@router.put(
    "/{id_nota}",
    response_model=NotaSeguimientoOut,
    summary="Modificar una anotación médica existente (médico creador)",
)
async def modificar_nota(
    id_nota: UUID,
    datos: NotaSeguimientoUpdate,
    session: SessionDep,
    medico: MedicoOAdminDep,
    request: Request,
) -> NotaSeguimientoOut:
    return await nota_service.modificar_nota_seguimiento(
        session,
        id_nota=id_nota,
        datos=datos,
        usuario_medico=medico,
        request=request,
    )


@router.get(
    "/paciente/{id_paciente}",
    response_model=list[NotaSeguimientoOut],
    summary="Listar las anotaciones médicas de un paciente (solo personal médico, P-23)",
)
async def listar_notas_paciente(
    id_paciente: UUID,
    session: SessionDep,
    medico: MedicoOAdminDep,
) -> list[NotaSeguimientoOut]:
    return await nota_service.listar_notas_paciente(
        session,
        id_paciente=id_paciente,
        usuario_actual=medico,
    )
