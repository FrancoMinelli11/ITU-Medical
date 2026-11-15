"""Mantenimiento de especialidades médicas (RF-18)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.exceptions import ApiError
from app.db.models.especialidad import Especialidad
from app.schemas.especialidad import (
    EspecialidadCreate,
    EspecialidadOut,
    EspecialidadUpdate,
)
from app.services import auditoria_service
from app.services.auditoria_service import Accion

ESPECIALIDAD_DUPLICADA = (
    409,
    "ESPECIALIDAD_DUPLICADA",
    "Especialidad ya registrada",
    "Ya existe una especialidad con ese nombre.",
)
ESPECIALIDAD_NO_ENCONTRADA = (
    404,
    "ESPECIALIDAD_NO_ENCONTRADA",
    "No encontrada",
    "La especialidad no existe.",
)


def _salida(especialidad: Especialidad) -> EspecialidadOut:
    return EspecialidadOut(
        id_especialidad=especialidad.id_especialidad,
        nombre=especialidad.nombre,
        descripcion=especialidad.descripcion,
        activa=especialidad.activa,
        fecha_creacion=especialidad.fecha_creacion,
    )


async def listar(session: AsyncSession, *, solo_activas: bool = False) -> list[EspecialidadOut]:
    consulta = select(Especialidad).order_by(Especialidad.nombre)
    if solo_activas:
        consulta = consulta.where(Especialidad.activa.is_(True))

    filas = (await session.scalars(consulta)).all()
    return [_salida(esp) for esp in filas]


async def obtener(session: AsyncSession, id_especialidad: UUID) -> EspecialidadOut:
    especialidad = await session.get(Especialidad, id_especialidad)
    if especialidad is None:
        raise ApiError(*ESPECIALIDAD_NO_ENCONTRADA)
    return _salida(especialidad)


async def crear(
    session: AsyncSession, *, payload: EspecialidadCreate, request: Request
) -> EspecialidadOut:
    existente = await session.scalar(
        select(Especialidad).where(
            func.lower(Especialidad.nombre) == payload.nombre.strip().lower()
        )
    )
    if existente is not None:
        raise ApiError(*ESPECIALIDAD_DUPLICADA)

    especialidad = Especialidad(
        nombre=payload.nombre.strip(),
        descripcion=payload.descripcion.strip() if payload.descripcion else None,
        activa=True,
    )
    session.add(especialidad)
    await session.flush()

    await auditoria_service.registrar(
        session,
        accion=Accion.ALTA_ESPECIALIDAD,
        entidad="especialidad",
        entidad_id=especialidad.id_especialidad,
        datos_despues={"nombre": especialidad.nombre},
        request=request,
        commit=False,
    )
    await session.commit()
    return _salida(especialidad)


async def actualizar(
    session: AsyncSession,
    *,
    id_especialidad: UUID,
    payload: EspecialidadUpdate,
    request: Request,
) -> EspecialidadOut:
    especialidad = await session.get(Especialidad, id_especialidad)
    if especialidad is None:
        raise ApiError(*ESPECIALIDAD_NO_ENCONTRADA)

    cambios = payload.model_dump(exclude_unset=True)
    antes: dict[str, object] = {}
    despues: dict[str, object] = {}

    if "nombre" in cambios and cambios["nombre"] is not None:
        nuevo_nombre = str(cambios["nombre"]).strip()
        if nuevo_nombre.lower() != especialidad.nombre.lower():
            conflicto = await session.scalar(
                select(Especialidad.id_especialidad).where(
                    func.lower(Especialidad.nombre) == nuevo_nombre.lower(),
                    Especialidad.id_especialidad != id_especialidad,
                )
            )
            if conflicto is not None:
                raise ApiError(*ESPECIALIDAD_DUPLICADA)

            antes["nombre"] = especialidad.nombre
            especialidad.nombre = nuevo_nombre
            despues["nombre"] = nuevo_nombre

    if "descripcion" in cambios:
        nueva_desc = str(cambios["descripcion"]).strip() if cambios["descripcion"] else None
        if nueva_desc != especialidad.descripcion:
            antes["descripcion"] = especialidad.descripcion
            especialidad.descripcion = nueva_desc
            despues["descripcion"] = nueva_desc

    if "activa" in cambios and cambios["activa"] is not None:
        if cambios["activa"] != especialidad.activa:
            antes["activa"] = especialidad.activa
            especialidad.activa = bool(cambios["activa"])
            despues["activa"] = especialidad.activa

    if not despues:
        return _salida(especialidad)

    await auditoria_service.registrar(
        session,
        accion=Accion.MODIFICACION_ESPECIALIDAD,
        entidad="especialidad",
        entidad_id=especialidad.id_especialidad,
        datos_antes=antes,
        datos_despues=despues,
        request=request,
        commit=False,
    )
    await session.commit()
    return _salida(especialidad)
