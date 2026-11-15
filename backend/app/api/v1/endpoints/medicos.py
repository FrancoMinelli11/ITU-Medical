"""Médicos: profesionales, horarios, bloqueos y disponibilidad (RF-04, RF-17, RF-18, RF-26)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import CurrentUser, SessionDep, require_roles
from app.core.exceptions import ApiError
from app.db.models.enums import RolUsuario
from app.db.models.medico import Medico
from app.db.models.usuario import Usuario
from app.schemas.agenda import (
    AgendaOut,
    BloqueoCreate,
    BloqueoOut,
    DisponibilidadOut,
    HorarioOut,
    HorariosSetRequest,
)
from app.schemas.common import Pagina
from app.schemas.medico import MedicoCreate, MedicoOut, MedicoUpdate
from app.services import agenda_service, medico_service

router = APIRouter()

AdminDep = Annotated[Usuario, Depends(require_roles(RolUsuario.ADMINISTRADOR))]
StaffDep = Annotated[
    Usuario,
    Depends(require_roles(RolUsuario.RECEPCIONISTA, RolUsuario.ADMINISTRADOR)),
]


async def _validar_acceso_agenda_o_bloqueo(
    usuario: Usuario, id_medico: UUID, session: SessionDep
) -> None:
    """Admin y Recepción tienen acceso a todos; un médico solo a su propia agenda."""
    if usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCIONISTA):
        return

    if usuario.rol == RolUsuario.MEDICO:
        medico = await session.get(Medico, id_medico)
        if medico is not None and medico.id_usuario == usuario.id_usuario:
            return

    raise ApiError(
        403,
        "SIN_PERMISO",
        "Sin permiso",
        "No tenés permisos para consultar o modificar la agenda de este profesional.",
    )


# ==============================================================================
# 1. Profesionales (Médicos)
# ==============================================================================


@router.get("", response_model=Pagina[MedicoOut], summary="Listar médicos")
async def listar_medicos(
    usuario: CurrentUser,
    session: SessionDep,
    q: Annotated[
        str | None,
        Query(max_length=80, description="DNI, nombre, apellido o matrícula"),
    ] = None,
    id_especialidad: Annotated[
        UUID | None,
        Query(description="Filtrar por especialidad"),
    ] = None,
    solo_activos: Annotated[
        bool,
        Query(description="Filtrar solo profesionales activos"),
    ] = True,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Pagina[MedicoOut]:
    filtro_activos = solo_activos if usuario.rol == RolUsuario.ADMINISTRADOR else True
    return await medico_service.listar(
        session,
        q=q,
        id_especialidad=id_especialidad,
        solo_activos=filtro_activos,
        page=page,
        page_size=page_size,
    )


@router.get("/{id_medico}", response_model=MedicoOut, summary="Obtener detalle de médico")
async def obtener_medico(
    id_medico: UUID,
    usuario: CurrentUser,
    session: SessionDep,
) -> MedicoOut:
    return await medico_service.obtener(session, id_medico)


@router.post(
    "",
    response_model=MedicoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear médico (Administrador)",
)
async def crear_medico(
    payload: MedicoCreate,
    request: Request,
    admin: AdminDep,
    session: SessionDep,
) -> MedicoOut:
    return await medico_service.crear(session, payload=payload, request=request)


@router.patch(
    "/{id_medico}",
    response_model=MedicoOut,
    summary="Modificar médico (Administrador)",
)
async def actualizar_medico(
    id_medico: UUID,
    payload: MedicoUpdate,
    request: Request,
    admin: AdminDep,
    session: SessionDep,
) -> MedicoOut:
    return await medico_service.actualizar(
        session, id_medico=id_medico, payload=payload, request=request
    )


# ==============================================================================
# 2. Horarios de atención habitual
# ==============================================================================


@router.get(
    "/{id_medico}/horarios",
    response_model=list[HorarioOut],
    summary="Consultar horarios de atención habitual",
)
async def obtener_horarios(
    id_medico: UUID,
    usuario: CurrentUser,
    session: SessionDep,
) -> list[HorarioOut]:
    return await agenda_service.obtener_horarios(session, id_medico)


@router.put(
    "/{id_medico}/horarios",
    response_model=list[HorarioOut],
    summary="Configurar horarios habituales (Administrador)",
)
async def configurar_horarios(
    id_medico: UUID,
    payload: HorariosSetRequest,
    request: Request,
    admin: AdminDep,
    session: SessionDep,
) -> list[HorarioOut]:
    return await agenda_service.configurar_horarios(
        session, id_medico=id_medico, payload=payload, request=request
    )


# ==============================================================================
# 3. Disponibilidad de turnos
# ==============================================================================


@router.get(
    "/{id_medico}/disponibilidad",
    response_model=DisponibilidadOut,
    summary="Consultar slots disponibles para reservar",
)
async def consultar_disponibilidad(
    id_medico: UUID,
    usuario: CurrentUser,
    session: SessionDep,
    fecha_desde: Annotated[date, Query(description="Fecha inicio (YYYY-MM-DD)")],
    fecha_hasta: Annotated[date, Query(description="Fecha fin (YYYY-MM-DD)")],
) -> DisponibilidadOut:
    return await agenda_service.calcular_disponibilidad(
        session,
        id_medico=id_medico,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


# ==============================================================================
# 4. Bloqueos de agenda
# ==============================================================================


@router.get(
    "/{id_medico}/bloqueos",
    response_model=list[BloqueoOut],
    summary="Listar bloqueos de agenda",
)
async def listar_bloqueos(
    id_medico: UUID,
    usuario: CurrentUser,
    session: SessionDep,
    desde: Annotated[datetime | None, Query()] = None,
    hasta: Annotated[datetime | None, Query()] = None,
) -> list[BloqueoOut]:
    await _validar_acceso_agenda_o_bloqueo(usuario, id_medico, session)
    return await agenda_service.obtener_bloqueos(
        session, id_medico=id_medico, desde=desde, hasta=hasta
    )


@router.post(
    "/{id_medico}/bloqueos",
    response_model=BloqueoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar bloqueo de agenda (Administración o Recepción)",
)
async def crear_bloqueo(
    id_medico: UUID,
    payload: BloqueoCreate,
    request: Request,
    staff: StaffDep,
    session: SessionDep,
) -> BloqueoOut:
    return await agenda_service.crear_bloqueo(
        session,
        id_medico=id_medico,
        payload=payload,
        usuario_creador=staff,
        request=request,
    )


@router.delete(
    "/{id_medico}/bloqueos/{id_bloqueo}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancelar bloqueo de agenda (Administración o Recepción)",
)
async def eliminar_bloqueo(
    id_medico: UUID,
    id_bloqueo: UUID,
    request: Request,
    staff: StaffDep,
    session: SessionDep,
) -> None:
    await agenda_service.eliminar_bloqueo(
        session, id_medico=id_medico, id_bloqueo=id_bloqueo, request=request
    )


# ==============================================================================
# 5. Vista de Agenda
# ==============================================================================


@router.get(
    "/{id_medico}/agenda",
    response_model=AgendaOut,
    summary="Ver agenda completa de turnos y bloqueos",
)
async def ver_agenda(
    id_medico: UUID,
    usuario: CurrentUser,
    session: SessionDep,
    fecha_desde: Annotated[date, Query(description="Fecha inicio (YYYY-MM-DD)")],
    fecha_hasta: Annotated[date, Query(description="Fecha fin (YYYY-MM-DD)")],
) -> AgendaOut:
    await _validar_acceso_agenda_o_bloqueo(usuario, id_medico, session)
    return await agenda_service.obtener_agenda(
        session,
        id_medico=id_medico,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
