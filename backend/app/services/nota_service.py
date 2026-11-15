"""Servicio de registro de atención y notas médicas de seguimiento.

Cumple con RF-13, RF-14, P-22, P-23 y T-RF13.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.exceptions import ApiError
from app.core.timezone import now_utc
from app.db.models.enums import EstadoTurno, RolUsuario
from app.db.models.especialidad import Especialidad
from app.db.models.medico import Medico
from app.db.models.nota_seguimiento import NotaSeguimiento
from app.db.models.paciente import Paciente
from app.db.models.turno import Turno
from app.db.models.usuario import Usuario
from app.schemas.nota import (
    NotaSeguimientoCreate,
    NotaSeguimientoOut,
    NotaSeguimientoUpdate,
)
from app.schemas.turno import TurnoResponse
from app.services import auditoria_service
from app.services.auditoria_service import Accion

TURNO_NO_ENCONTRADO = (
    404,
    "TURNO_NO_ENCONTRADO",
    "Turno no encontrado",
    "El turno solicitado no existe.",
)
NOTA_NO_ENCONTRADA = (
    404,
    "NOTA_NO_ENCONTRADA",
    "Nota no encontrada",
    "La anotación médica solicitada no existe.",
)
PACIENTE_NO_ENCONTRADO = (
    404,
    "PACIENTE_NO_ENCONTRADO",
    "Paciente no encontrado",
    "El paciente indicado no existe.",
)


def _armar_turno_response(
    turno: Turno,
    medico_usuario: Usuario,
    especialidad: Especialidad,
    paciente_usuario: Usuario,
) -> TurnoResponse:
    return TurnoResponse(
        id_turno=turno.id_turno,
        id_paciente=turno.id_paciente,
        id_medico=turno.id_medico,
        fecha_hora=turno.fecha_hora,
        duracion_minutos=turno.duracion_minutos,
        estado=turno.estado,
        fecha_hora_llegada=turno.fecha_hora_llegada,
        fecha_hora_cancelacion=turno.fecha_hora_cancelacion,
        motivo_cancelacion=turno.motivo_cancelacion,
        detalle_cancelacion=turno.detalle_cancelacion,
        medico_nombre=medico_usuario.nombre,
        medico_apellido=medico_usuario.apellido,
        especialidad_nombre=especialidad.nombre,
        paciente_nombre=paciente_usuario.nombre,
        paciente_apellido=paciente_usuario.apellido,
        paciente_dni=paciente_usuario.dni,
        fecha_creacion=turno.fecha_creacion,
    )


async def registrar_atencion(
    session: AsyncSession,
    *,
    id_turno: UUID,
    usuario_medico: Usuario,
    request: Request | None = None,
) -> TurnoResponse:
    """Registra la atención y finalización del turno por el profesional asignado.

    Cumple con RF-13, CU-08 y T-RF13.
    """
    turno = await session.get(Turno, id_turno)
    if turno is None:
        raise ApiError(*TURNO_NO_ENCONTRADO)

    medico = await session.scalar(
        select(Medico).where(Medico.id_usuario == usuario_medico.id_usuario)
    )
    if usuario_medico.rol == RolUsuario.MEDICO:
        if medico is None or turno.id_medico != medico.id_medico:
            raise ApiError(
                403,
                "ACCESO_DENEGADO",
                "Profesional no asignado",
                "No podés registrar la atención de un turno asignado a otro profesional.",
            )

    # Validar transiciones según tabla de transiciones: solo EN_ESPERA -> ATENDIDO
    if turno.estado != EstadoTurno.EN_ESPERA:
        if turno.estado == EstadoTurno.RESERVADO:
            raise ApiError(
                400,
                "TRANSICION_INVALIDA",
                "Paciente no anunciado",
                "El paciente debe registrar su llegada en recepción antes de ser atendido.",
            )
        raise ApiError(
            400,
            "TRANSICION_INVALIDA",
            "Transición no permitida",
            f"No se puede registrar atención para un turno en estado {turno.estado.value}.",
        )

    turno.estado = EstadoTurno.ATENDIDO

    medico_obj = await session.get(Medico, turno.id_medico)
    assert medico_obj is not None
    medico_usuario = await session.get(Usuario, medico_obj.id_usuario)
    especialidad = await session.get(Especialidad, medico_obj.id_especialidad)
    paciente = await session.get(Paciente, turno.id_paciente)
    assert paciente is not None
    paciente_usuario = await session.get(Usuario, paciente.id_usuario)
    assert medico_usuario and especialidad and paciente_usuario

    await auditoria_service.registrar(
        session,
        accion=Accion.ATENCION_TURNO,
        id_usuario=usuario_medico.id_usuario,
        entidad="turno",
        entidad_id=turno.id_turno,
        request=request,
    )

    await session.commit()
    return _armar_turno_response(turno, medico_usuario, especialidad, paciente_usuario)


async def crear_nota_seguimiento(
    session: AsyncSession,
    *,
    datos: NotaSeguimientoCreate,
    usuario_medico: Usuario,
    request: Request | None = None,
) -> NotaSeguimientoOut:
    """Registra una nota de seguimiento médico para un paciente (RF-14, P-22, P-23)."""
    medico = await session.scalar(
        select(Medico).where(Medico.id_usuario == usuario_medico.id_usuario)
    )
    if medico is None and usuario_medico.rol != RolUsuario.ADMINISTRADOR:
        raise ApiError(
            403,
            "ACCESO_DENEGADO",
            "Permisos insuficientes",
            "Solo los profesionales médicos pueden registrar notas de seguimiento.",
        )

    paciente = await session.get(Paciente, datos.id_paciente)
    if paciente is None:
        raise ApiError(*PACIENTE_NO_ENCONTRADO)

    id_medico_final = (
        medico.id_medico if medico else (await session.scalar(select(Medico.id_medico)))
    )
    assert id_medico_final is not None

    nota = NotaSeguimiento(
        id_medico=id_medico_final,
        id_paciente=datos.id_paciente,
        id_turno=datos.id_turno,
        contenido=datos.contenido,
        fecha_creacion=now_utc(),
        fecha_modificacion=now_utc(),
    )
    session.add(nota)
    await session.flush()

    await auditoria_service.registrar(
        session,
        accion=Accion.ALTA_NOTA_MEDICA,
        id_usuario=usuario_medico.id_usuario,
        entidad="nota_seguimiento",
        entidad_id=nota.id_nota,
        request=request,
    )

    await session.commit()

    medico_actual = await session.get(Medico, id_medico_final)
    assert medico_actual is not None
    m_usr = await session.get(Usuario, medico_actual.id_usuario)
    esp = await session.get(Especialidad, medico_actual.id_especialidad)

    return NotaSeguimientoOut(
        id_nota=nota.id_nota,
        id_medico=nota.id_medico,
        id_paciente=nota.id_paciente,
        id_turno=nota.id_turno,
        contenido=nota.contenido,
        fecha_creacion=nota.fecha_creacion,
        fecha_modificacion=nota.fecha_modificacion,
        medico_nombre=m_usr.nombre if m_usr else None,
        medico_apellido=m_usr.apellido if m_usr else None,
        especialidad_nombre=esp.nombre if esp else None,
    )


async def modificar_nota_seguimiento(
    session: AsyncSession,
    *,
    id_nota: UUID,
    datos: NotaSeguimientoUpdate,
    usuario_medico: Usuario,
    request: Request | None = None,
) -> NotaSeguimientoOut:
    """Modifica una nota médica existente (RF-14, P-23)."""
    nota = await session.get(NotaSeguimiento, id_nota)
    if nota is None:
        raise ApiError(*NOTA_NO_ENCONTRADA)

    medico = await session.scalar(
        select(Medico).where(Medico.id_usuario == usuario_medico.id_usuario)
    )
    if usuario_medico.rol == RolUsuario.MEDICO:
        if medico is None or nota.id_medico != medico.id_medico:
            raise ApiError(
                403,
                "ACCESO_DENEGADO",
                "Permisos insuficientes",
                "No podés modificar una anotación médica creada por otro profesional.",
            )

    nota.contenido = datos.contenido
    nota.fecha_modificacion = now_utc()

    await auditoria_service.registrar(
        session,
        accion=Accion.MODIFICACION_NOTA_MEDICA,
        id_usuario=usuario_medico.id_usuario,
        entidad="nota_seguimiento",
        entidad_id=nota.id_nota,
        request=request,
    )

    await session.commit()

    medico_actual = await session.get(Medico, nota.id_medico)
    assert medico_actual is not None
    m_usr = await session.get(Usuario, medico_actual.id_usuario)
    esp = await session.get(Especialidad, medico_actual.id_especialidad)

    return NotaSeguimientoOut(
        id_nota=nota.id_nota,
        id_medico=nota.id_medico,
        id_paciente=nota.id_paciente,
        id_turno=nota.id_turno,
        contenido=nota.contenido,
        fecha_creacion=nota.fecha_creacion,
        fecha_modificacion=nota.fecha_modificacion,
        medico_nombre=m_usr.nombre if m_usr else None,
        medico_apellido=m_usr.apellido if m_usr else None,
        especialidad_nombre=esp.nombre if esp else None,
    )


async def listar_notas_paciente(
    session: AsyncSession,
    *,
    id_paciente: UUID,
    usuario_actual: Usuario,
) -> list[NotaSeguimientoOut]:
    """Lista las anotaciones médicas del paciente (RF-14, P-23: confidencialidad clínica)."""
    if usuario_actual.rol not in (RolUsuario.MEDICO, RolUsuario.ADMINISTRADOR):
        raise ApiError(
            403,
            "ACCESO_DENEGADO",
            "Permisos insuficientes",
            "Solo los profesionales médicos tienen acceso a las anotaciones de seguimiento.",
        )

    stmt = (
        select(NotaSeguimiento, Medico, Usuario, Especialidad)
        .join(Medico, Medico.id_medico == NotaSeguimiento.id_medico)
        .join(Usuario, Usuario.id_usuario == Medico.id_usuario)
        .join(Especialidad, Especialidad.id_especialidad == Medico.id_especialidad)
        .where(NotaSeguimiento.id_paciente == id_paciente)
        .order_by(NotaSeguimiento.fecha_creacion.desc())
    )
    filas = (await session.execute(stmt)).all()

    items: list[NotaSeguimientoOut] = []
    for fila in filas:
        nota = fila[0]
        m_usr = fila[2]
        esp = fila[3]
        items.append(
            NotaSeguimientoOut(
                id_nota=nota.id_nota,
                id_medico=nota.id_medico,
                id_paciente=nota.id_paciente,
                id_turno=nota.id_turno,
                contenido=nota.contenido,
                fecha_creacion=nota.fecha_creacion,
                fecha_modificacion=nota.fecha_modificacion,
                medico_nombre=m_usr.nombre,
                medico_apellido=m_usr.apellido,
                especialidad_nombre=esp.nombre,
            )
        )
    return items
