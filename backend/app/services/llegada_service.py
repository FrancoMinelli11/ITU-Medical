"""Servicio de gestión de llegadas, sala de espera y ausencias (RF-11, RF-12, RF-15)."""

from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from starlette.requests import Request

from app.core.exceptions import ApiError
from app.core.timezone import LOCAL_TZ, now_utc, to_local, to_utc
from app.db.models.enums import EstadoTurno
from app.db.models.especialidad import Especialidad
from app.db.models.medico import Medico
from app.db.models.paciente import Paciente
from app.db.models.turno import Turno
from app.db.models.usuario import Usuario
from app.domain.orden_atencion import esta_en_tolerancia, ordenar_pacientes_en_espera
from app.schemas.recepcion import CierreJornadaResponse, TurnoEnEsperaResponse
from app.schemas.turno import TurnoResponse
from app.services import auditoria_service
from app.services.auditoria_service import Accion

TURNO_NO_ENCONTRADO = (
    404,
    "TURNO_NO_ENCONTRADO",
    "Turno no encontrado",
    "El turno solicitado no existe.",
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


async def registrar_llegada(
    session: AsyncSession,
    *,
    id_turno: UUID,
    usuario_staff: Usuario,
    request: Request | None = None,
) -> TurnoResponse:
    """Registra la llegada de un paciente al centro médico (RF-11, CU-07, P-17, P-18)."""
    turno = await session.get(Turno, id_turno)
    if turno is None:
        raise ApiError(*TURNO_NO_ENCONTRADO)

    # Prevenir llegada duplicada (P-18)
    if turno.estado == EstadoTurno.EN_ESPERA:
        raise ApiError(
            409,
            "LLEGADA_YA_REGISTRADA",
            "Llegada ya registrada",
            "La llegada del paciente ya fue registrada previamente para este turno.",
        )

    if turno.estado != EstadoTurno.RESERVADO:
        raise ApiError(
            400,
            "TRANSICION_INVALIDA",
            "Transición no permitida",
            f"No se puede registrar llegada para un turno en estado {turno.estado.value}.",
        )

    ahora = now_utc()
    turno.estado = EstadoTurno.EN_ESPERA
    turno.fecha_hora_llegada = ahora

    medico = await session.get(Medico, turno.id_medico)
    assert medico is not None
    medico_usuario = await session.get(Usuario, medico.id_usuario)
    especialidad = await session.get(Especialidad, medico.id_especialidad)
    paciente = await session.get(Paciente, turno.id_paciente)
    assert paciente is not None
    paciente_usuario = await session.get(Usuario, paciente.id_usuario)
    assert medico_usuario and especialidad and paciente_usuario

    await auditoria_service.registrar(
        session,
        accion=Accion.REGISTRO_LLEGADA,
        id_usuario=usuario_staff.id_usuario,
        entidad="turno",
        entidad_id=turno.id_turno,
        request=request,
    )

    await session.commit()
    return _armar_turno_response(turno, medico_usuario, especialidad, paciente_usuario)


async def obtener_sala_espera(
    session: AsyncSession,
    *,
    id_medico: UUID | None = None,
    fecha: date | None = None,
) -> list[TurnoEnEsperaResponse]:
    """Obtiene y organiza la sala de espera según el algoritmo de prioridad (RF-12, P-19, P-20)."""
    fecha_consulta = fecha or to_local(now_utc()).date()
    inicio_dia_utc = to_utc(datetime.combine(fecha_consulta, time.min, tzinfo=LOCAL_TZ))
    fin_dia_utc = to_utc(datetime.combine(fecha_consulta, time.max, tzinfo=LOCAL_TZ))

    UsuarioMedico = aliased(Usuario, name="medico_usr")
    UsuarioPaciente = aliased(Usuario, name="paciente_usr")

    stmt = (
        select(Turno, Medico, UsuarioMedico, Especialidad, Paciente, UsuarioPaciente)
        .join(Medico, Medico.id_medico == Turno.id_medico)
        .join(UsuarioMedico, UsuarioMedico.id_usuario == Medico.id_usuario)
        .join(Especialidad, Especialidad.id_especialidad == Medico.id_especialidad)
        .join(Paciente, Paciente.id_paciente == Turno.id_paciente)
        .join(UsuarioPaciente, UsuarioPaciente.id_usuario == Paciente.id_usuario)
        .where(
            Turno.estado == EstadoTurno.EN_ESPERA,
            Turno.fecha_hora >= inicio_dia_utc,
            Turno.fecha_hora <= fin_dia_utc,
        )
    )

    if id_medico is not None:
        stmt = stmt.where(Turno.id_medico == id_medico)

    resultados = (await session.execute(stmt)).all()
    if not resultados:
        return []

    # Extraer turnos y ordenarlos con el algoritmo de orden de atención (RF-12)
    turnos_ordenados = ordenar_pacientes_en_espera([r[0] for r in resultados])

    # Indexar la información relacionada
    info_map = {r[0].id_turno: (r[2], r[3], r[5]) for r in resultados}

    respuestas: list[TurnoEnEsperaResponse] = []
    for idx, t in enumerate(turnos_ordenados, start=1):
        med_usr, esp, pac_usr = info_map[t.id_turno]
        en_tol = esta_en_tolerancia(t.fecha_hora, t.fecha_hora_llegada)
        respuestas.append(
            TurnoEnEsperaResponse(
                id_turno=t.id_turno,
                id_paciente=t.id_paciente,
                id_medico=t.id_medico,
                paciente_nombre=pac_usr.nombre,
                paciente_apellido=pac_usr.apellido,
                paciente_dni=pac_usr.dni,
                medico_nombre=med_usr.nombre,
                medico_apellido=med_usr.apellido,
                especialidad_nombre=esp.nombre,
                fecha_hora=t.fecha_hora,
                fecha_hora_llegada=t.fecha_hora_llegada or t.fecha_hora,
                duracion_minutos=t.duracion_minutos,
                en_tolerancia=en_tol,
                orden_atencion=idx,
            )
        )

    return respuestas


async def registrar_ausencia_individual(
    session: AsyncSession,
    *,
    id_turno: UUID,
    usuario_staff: Usuario,
    request: Request | None = None,
) -> TurnoResponse:
    """Marca individualmente un turno no asistido como AUSENTE (RF-15, P-21)."""
    turno = await session.get(Turno, id_turno)
    if turno is None:
        raise ApiError(*TURNO_NO_ENCONTRADO)

    if turno.estado != EstadoTurno.RESERVADO:
        raise ApiError(
            400,
            "TRANSICION_INVALIDA",
            "Transición no permitida",
            "Solo se pueden marcar ausencias para turnos en estado RESERVADO "
            f"(actual: {turno.estado.value}).",
        )

    turno.estado = EstadoTurno.AUSENTE

    medico = await session.get(Medico, turno.id_medico)
    assert medico is not None
    medico_usuario = await session.get(Usuario, medico.id_usuario)
    especialidad = await session.get(Especialidad, medico.id_especialidad)
    paciente = await session.get(Paciente, turno.id_paciente)
    assert paciente is not None
    paciente_usuario = await session.get(Usuario, paciente.id_usuario)
    assert medico_usuario and especialidad and paciente_usuario

    await auditoria_service.registrar(
        session,
        accion=Accion.REGISTRO_AUSENCIA,
        id_usuario=usuario_staff.id_usuario,
        entidad="turno",
        entidad_id=turno.id_turno,
        request=request,
    )

    await session.commit()
    return _armar_turno_response(turno, medico_usuario, especialidad, paciente_usuario)


async def cerrar_jornada_ausencias(
    session: AsyncSession,
    *,
    usuario_staff: Usuario,
    fecha: date | None = None,
    request: Request | None = None,
) -> CierreJornadaResponse:
    """Cierra la jornada marcando ausencias de turnos que no registraron llegada (RF-15)."""
    fecha_consulta = fecha or to_local(now_utc()).date()
    fin_dia_utc = to_utc(datetime.combine(fecha_consulta, time.max, tzinfo=LOCAL_TZ))

    stmt = select(Turno).where(
        Turno.estado == EstadoTurno.RESERVADO,
        Turno.fecha_hora <= fin_dia_utc,
        Turno.fecha_hora_llegada.is_(None),
    )
    turnos = (await session.scalars(stmt)).all()

    turnos_afectados: list[UUID] = []
    for t in turnos:
        t.estado = EstadoTurno.AUSENTE
        turnos_afectados.append(t.id_turno)
        await auditoria_service.registrar(
            session,
            accion=Accion.REGISTRO_AUSENCIA,
            id_usuario=usuario_staff.id_usuario,
            entidad="turno",
            entidad_id=t.id_turno,
            request=request,
        )

    await session.commit()
    return CierreJornadaResponse(
        total_ausentes=len(turnos_afectados),
        turnos_afectados=turnos_afectados,
    )
