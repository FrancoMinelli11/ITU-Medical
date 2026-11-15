"""Especialidades médicas: catálogo, alta y modificación (RF-18)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import CurrentUser, SessionDep, require_roles
from app.db.models.enums import RolUsuario
from app.db.models.usuario import Usuario
from app.schemas.especialidad import (
    EspecialidadCreate,
    EspecialidadOut,
    EspecialidadUpdate,
)
from app.services import especialidad_service

router = APIRouter()

AdminDep = Annotated[Usuario, Depends(require_roles(RolUsuario.ADMINISTRADOR))]


@router.get("", response_model=list[EspecialidadOut], summary="Listar especialidades")
async def listar(
    usuario: CurrentUser,
    session: SessionDep,
    solo_activas: bool = Query(default=True, description="Filtrar solo especialidades activas"),
) -> list[EspecialidadOut]:
    # Los usuarios que no son admin solo ven activas por seguridad del catálogo
    filtro_activas = solo_activas if usuario.rol == RolUsuario.ADMINISTRADOR else True
    return await especialidad_service.listar(session, solo_activas=filtro_activas)


@router.get("/{id_especialidad}", response_model=EspecialidadOut, summary="Obtener especialidad")
async def obtener(
    id_especialidad: UUID,
    usuario: CurrentUser,
    session: SessionDep,
) -> EspecialidadOut:
    return await especialidad_service.obtener(session, id_especialidad)


@router.post(
    "",
    response_model=EspecialidadOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear especialidad (Administrador)",
)
async def crear(
    payload: EspecialidadCreate,
    request: Request,
    admin: AdminDep,
    session: SessionDep,
) -> EspecialidadOut:
    return await especialidad_service.crear(session, payload=payload, request=request)


@router.patch(
    "/{id_especialidad}",
    response_model=EspecialidadOut,
    summary="Modificar especialidad (Administrador)",
)
async def actualizar(
    id_especialidad: UUID,
    payload: EspecialidadUpdate,
    request: Request,
    admin: AdminDep,
    session: SessionDep,
) -> EspecialidadOut:
    return await especialidad_service.actualizar(
        session, id_especialidad=id_especialidad, payload=payload, request=request
    )
