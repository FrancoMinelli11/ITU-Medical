"""Servicio de gestión de restricciones y Usuario rojo (RF-16, RN-20..RN-22, RN-36)."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.exceptions import ApiError
from app.core.timezone import now_utc, to_local
from app.db.models.enums import TipoNotificacion
from app.db.models.paciente import Paciente
from app.db.models.restriccion_usuario import RestriccionUsuario
from app.db.models.usuario import Usuario
from app.schemas.restriccion import (
    RestriccionCreate,
    RestriccionEstadoOut,
    RestriccionOut,
)
from app.services import auditoria_service, notificacion_service
from app.services.auditoria_service import Accion

PACIENTE_NO_ENCONTRADO = (
    404,
    "PACIENTE_NO_ENCONTRADO",
    "Paciente no encontrado",
    "El paciente indicado no existe.",
)
RESTRICCION_NO_ENCONTRADA = (
    404,
    "RESTRICCION_NO_ENCONTRADA",
    "Restricción no encontrada",
    "La restricción solicitada no existe.",
)


def _armar_restriccion_out(
    restriccion: RestriccionUsuario,
    paciente_usuario: Usuario,
    id_paciente: UUID | None = None,
) -> RestriccionOut:
    ahora = now_utc()
    vigente = restriccion.activa and restriccion.fecha_fin > ahora
    return RestriccionOut(
        id_restriccion=restriccion.id_restriccion,
        id_usuario=restriccion.id_usuario,
        id_paciente=id_paciente,
        motivo=restriccion.motivo,
        fecha_inicio=restriccion.fecha_inicio,
        fecha_fin=restriccion.fecha_fin,
        activa=restriccion.activa,
        vigente=vigente,
        id_usuario_creador=restriccion.id_usuario_creador,
        fecha_creacion=restriccion.fecha_creacion,
        paciente_nombre=paciente_usuario.nombre,
        paciente_apellido=paciente_usuario.apellido,
        paciente_dni=paciente_usuario.dni,
    )


async def clasificar_usuario_rojo(
    session: AsyncSession,
    *,
    datos: RestriccionCreate,
    usuario_operador: Usuario,
    request: Request | None = None,
) -> RestriccionOut:
    """Clasifica a un paciente como Usuario rojo por 30 días (RF-16, RN-20, RN-36, P-24)."""
    paciente = await session.get(Paciente, datos.id_paciente)
    if paciente is None:
        raise ApiError(*PACIENTE_NO_ENCONTRADO)

    paciente_usuario = await session.get(Usuario, paciente.id_usuario)
    assert paciente_usuario is not None

    ahora = now_utc()

    # Verificar si ya existe una restricción activa vigente
    stmt_existente = select(RestriccionUsuario).where(
        RestriccionUsuario.id_usuario == paciente.id_usuario,
        RestriccionUsuario.activa.is_(True),
    )
    restriccion_actual = await session.scalar(stmt_existente)
    if restriccion_actual is not None:
        if restriccion_actual.fecha_fin > ahora:
            raise ApiError(
                409,
                "USUARIO_YA_RESTRINGIDO",
                "Restricción ya activa",
                "El paciente ya cuenta con una restricción vigente de Usuario rojo.",
            )
        # Si ya venció en el tiempo pero seguía activa=True, desactivar la anterior
        # para respetar el índice único uq_restriccion_activa_por_usuario
        restriccion_actual.activa = False

    fecha_inicio = ahora
    fecha_fin = ahora + timedelta(days=datos.dias_vigencia)

    nueva_restriccion = RestriccionUsuario(
        id_usuario=paciente.id_usuario,
        motivo=datos.motivo,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        activa=True,
        id_usuario_creador=usuario_operador.id_usuario,
        fecha_creacion=fecha_inicio,
    )
    session.add(nueva_restriccion)
    await session.flush()

    # Encolar notificación al paciente
    notif = notificacion_service.crear(
        session,
        usuario=paciente_usuario,
        tipo=TipoNotificacion.RESTRICCION_USUARIO_ROJO,
    )

    await auditoria_service.registrar(
        session,
        accion=Accion.ALTA_RESTRICCION_USUARIO,
        id_usuario=usuario_operador.id_usuario,
        entidad="restriccion_usuario",
        entidad_id=nueva_restriccion.id_restriccion,
        datos_despues={
            "motivo": datos.motivo,
            "dias_vigencia": datos.dias_vigencia,
            "fecha_fin": fecha_fin.isoformat(),
        },
        request=request,
    )

    await session.commit()

    fecha_fin_local = to_local(fecha_fin).strftime("%d/%m/%Y %H:%M")
    asunto, cuerpo = notificacion_service.cuerpo_restriccion_usuario_rojo(
        paciente_usuario,
        motivo=datos.motivo,
        fecha_fin_texto=fecha_fin_local,
    )
    await notificacion_service.despachar(
        notif,
        destinatario=paciente_usuario.email,
        asunto=asunto,
        cuerpo=cuerpo,
    )

    return _armar_restriccion_out(nueva_restriccion, paciente_usuario, paciente.id_paciente)


async def levantar_restriccion(
    session: AsyncSession,
    *,
    id_restriccion: UUID,
    usuario_operador: Usuario,
    request: Request | None = None,
) -> RestriccionOut:
    """Levanta o finaliza anticipadamente una restricción de Usuario rojo."""
    restriccion = await session.get(RestriccionUsuario, id_restriccion)
    if restriccion is None:
        raise ApiError(*RESTRICCION_NO_ENCONTRADA)

    paciente = await session.scalar(
        select(Paciente).where(Paciente.id_usuario == restriccion.id_usuario)
    )
    paciente_usuario = await session.get(Usuario, restriccion.id_usuario)
    assert paciente_usuario is not None

    restriccion.activa = False

    await auditoria_service.registrar(
        session,
        accion=Accion.BAJA_RESTRICCION_USUARIO,
        id_usuario=usuario_operador.id_usuario,
        entidad="restriccion_usuario",
        entidad_id=restriccion.id_restriccion,
        request=request,
    )

    await session.commit()
    id_paciente = paciente.id_paciente if paciente else None
    return _armar_restriccion_out(restriccion, paciente_usuario, id_paciente)


async def obtener_estado_paciente(
    session: AsyncSession,
    *,
    id_paciente: UUID,
) -> RestriccionEstadoOut:
    """Consulta el estado de restricción vigente de un paciente (RN-21, RN-36)."""
    paciente = await session.get(Paciente, id_paciente)
    if paciente is None:
        raise ApiError(*PACIENTE_NO_ENCONTRADO)

    paciente_usuario = await session.get(Usuario, paciente.id_usuario)
    assert paciente_usuario is not None

    ahora = now_utc()
    stmt = (
        select(RestriccionUsuario)
        .where(
            RestriccionUsuario.id_usuario == paciente.id_usuario,
            RestriccionUsuario.activa.is_(True),
        )
        .order_by(RestriccionUsuario.fecha_creacion.desc())
    )
    restriccion = await session.scalar(stmt)
    es_rojo = restriccion is not None and restriccion.fecha_fin > ahora

    restriccion_out = (
        _armar_restriccion_out(restriccion, paciente_usuario, paciente.id_paciente)
        if (restriccion is not None and es_rojo)
        else None
    )

    return RestriccionEstadoOut(
        id_paciente=paciente.id_paciente,
        id_usuario=paciente.id_usuario,
        es_usuario_rojo=es_rojo,
        restriccion_activa=restriccion_out,
    )


async def listar_restricciones(
    session: AsyncSession,
    *,
    solo_activas: bool = True,
    id_paciente: UUID | None = None,
) -> list[RestriccionOut]:
    """Lista las restricciones de usuarios registradas en el sistema."""
    ahora = now_utc()
    stmt = (
        select(RestriccionUsuario, Usuario, Paciente)
        .join(Usuario, Usuario.id_usuario == RestriccionUsuario.id_usuario)
        .outerjoin(Paciente, Paciente.id_usuario == Usuario.id_usuario)
        .order_by(RestriccionUsuario.fecha_creacion.desc())
    )
    if solo_activas:
        stmt = stmt.where(
            RestriccionUsuario.activa.is_(True),
            RestriccionUsuario.fecha_fin > ahora,
        )
    if id_paciente is not None:
        stmt = stmt.where(Paciente.id_paciente == id_paciente)

    filas = (await session.execute(stmt)).all()
    resultado: list[RestriccionOut] = []
    for fila in filas:
        rest: RestriccionUsuario = fila[0]
        usr: Usuario = fila[1]
        pac: Paciente | None = fila[2]
        id_pac = pac.id_paciente if pac else None
        resultado.append(_armar_restriccion_out(rest, usr, id_pac))
    return resultado
