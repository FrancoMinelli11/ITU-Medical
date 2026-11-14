"""Pacientes: búsqueda, alta desde recepción y edición (RF-02, CU-02).

Todos los endpoints exigen rol de recepción o administración **y** contraseña ya
actualizada (RN-29, C3): no alcanza con ocultar el botón en el SPA.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import SessionDep, require_roles
from app.db.models.enums import RolUsuario
from app.db.models.usuario import Usuario
from app.schemas.common import Pagina
from app.schemas.paciente import PacienteCreate, PacienteOut, PacienteUpdate
from app.services import paciente_service

router = APIRouter()

StaffDep = Annotated[
    Usuario, Depends(require_roles(RolUsuario.RECEPCIONISTA, RolUsuario.ADMINISTRADOR))
]


@router.get("", response_model=Pagina[PacienteOut], summary="Buscar pacientes")
async def listar(
    usuario: StaffDep,
    session: SessionDep,
    q: str | None = Query(
        default=None, max_length=80, description="DNI, nombre, apellido o correo"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Pagina[PacienteOut]:
    return await paciente_service.listar(session, q=q, page=page, page_size=page_size)


@router.post(
    "",
    response_model=PacienteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear paciente desde recepción",
)
async def crear(
    payload: PacienteCreate,
    request: Request,
    usuario: StaffDep,
    session: SessionDep,
) -> PacienteOut:
    """La contraseña inicial es el DNI y el correo queda verificado (RF-02)."""
    return await paciente_service.crear_desde_recepcion(session, payload=payload, request=request)


@router.get("/{id_paciente}", response_model=PacienteOut, summary="Ver un paciente")
async def obtener(id_paciente: UUID, usuario: StaffDep, session: SessionDep) -> PacienteOut:
    return await paciente_service.obtener(session, id_paciente)


@router.patch("/{id_paciente}", response_model=PacienteOut, summary="Editar un paciente")
async def actualizar(
    id_paciente: UUID,
    payload: PacienteUpdate,
    request: Request,
    usuario: StaffDep,
    session: SessionDep,
) -> PacienteOut:
    return await paciente_service.actualizar(
        session, id_paciente=id_paciente, payload=payload, request=request
    )
