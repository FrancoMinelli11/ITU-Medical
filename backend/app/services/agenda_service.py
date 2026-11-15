"""Lógica de agenda, horarios, bloqueos y disponibilidad médica (RF-04, RF-17, RF-26)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config import get_settings
from app.core.exceptions import ApiError
from app.core.timezone import LOCAL_TZ, now_utc, to_local, to_utc
from app.db.models.bloqueo_agenda import BloqueoAgenda
from app.db.models.enums import EstadoTurno
from app.db.models.horario_medico import HorarioMedico
from app.db.models.medico import Medico
from app.db.models.paciente import Paciente
from app.db.models.turno import Turno
from app.db.models.usuario import Usuario
from app.schemas.agenda import (
    AgendaOut,
    AgendaTurnoOut,
    BloqueoCreate,
    BloqueoOut,
    DisponibilidadOut,
    HorarioOut,
    HorariosSetRequest,
    SlotDisponibilidad,
)
from app.schemas.medico import TurnoAfectadoOut
from app.services import auditoria_service
from app.services.auditoria_service import Accion

settings = get_settings()

MEDICO_NO_ENCONTRADO = (
    404,
    "MEDICO_NO_ENCONTRADO",
    "No encontrado",
    "El médico no existe.",
)
BLOQUEO_NO_ENCONTRADO = (
    404,
    "BLOQUEO_NO_ENCONTRADO",
    "No encontrado",
    "El bloqueo de agenda no existe.",
)
RANGO_INVALIDO = (
    400,
    "RANGO_INVALIDO",
    "Rango de fechas inválido",
    "La fecha de fin debe ser posterior o igual a la de inicio.",
)
HORARIO_INVALIDO = (
    400,
    "HORARIO_INVALIDO",
    "Horario inválido",
    "La hora de inicio debe ser anterior a la hora de fin.",
)


def _salida_horario(horario: HorarioMedico) -> HorarioOut:
    return HorarioOut(
        id_horario=horario.id_horario,
        id_medico=horario.id_medico,
        dia_semana=horario.dia_semana,
        hora_inicio=horario.hora_inicio,
        hora_fin=horario.hora_fin,
        duracion_minutos=horario.duracion_minutos,
        activo=horario.activo,
    )


def _salida_bloqueo(bloqueo: BloqueoAgenda) -> BloqueoOut:
    return BloqueoOut(
        id_bloqueo=bloqueo.id_bloqueo,
        id_medico=bloqueo.id_medico,
        inicio=bloqueo.inicio,
        fin=bloqueo.fin,
        motivo=bloqueo.motivo,
        id_usuario_creador=bloqueo.id_usuario_creador,
        fecha_creacion=bloqueo.fecha_creacion,
    )


async def obtener_horarios(session: AsyncSession, id_medico: UUID) -> list[HorarioOut]:
    horarios = (
        await session.scalars(
            select(HorarioMedico)
            .where(HorarioMedico.id_medico == id_medico)
            .order_by(HorarioMedico.dia_semana, HorarioMedico.hora_inicio)
        )
    ).all()
    return [_salida_horario(h) for h in horarios]


async def configurar_horarios(
    session: AsyncSession,
    *,
    id_medico: UUID,
    payload: HorariosSetRequest,
    request: Request,
) -> list[HorarioOut]:
    medico = await session.get(Medico, id_medico)
    if medico is None:
        raise ApiError(*MEDICO_NO_ENCONTRADO)

    # 1. Validar rangos individuales y superposiciones internas
    horarios_ordenados = sorted(payload.horarios, key=lambda h: (h.dia_semana, h.hora_inicio))

    for i, h in enumerate(horarios_ordenados):
        if h.hora_inicio >= h.hora_fin:
            raise ApiError(*HORARIO_INVALIDO)
        if i > 0:
            anterior = horarios_ordenados[i - 1]
            if anterior.dia_semana == h.dia_semana and h.hora_inicio < anterior.hora_fin:
                raise ApiError(
                    400,
                    "HORARIOS_SUPERPUESTOS",
                    "Horarios superpuestos",
                    f"Existen horarios superpuestos para el día de la semana {h.dia_semana}.",
                )

    # 2. RF-17 / RF-26 / P-28: Verificar si deja turnos futuros activos fuera del horario
    ahora = now_utc()
    turnos_futuros = (
        await session.scalars(
            select(Turno)
            .where(
                Turno.id_medico == id_medico,
                Turno.estado.in_([EstadoTurno.RESERVADO, EstadoTurno.EN_ESPERA]),
                Turno.fecha_hora >= ahora,
            )
            .order_by(Turno.fecha_hora)
        )
    ).all()

    turnos_afectados: list[Turno] = []
    for turno in turnos_futuros:
        inicio_local = to_local(turno.fecha_hora)
        fin_local = inicio_local + timedelta(minutes=turno.duracion_minutos)
        dia_semana_turno = inicio_local.weekday()

        # Debe encajar completamente dentro de al menos un horario activo del día
        encaja = False
        for h in horarios_ordenados:
            if not h.activo or h.dia_semana != dia_semana_turno:
                continue
            if h.hora_inicio <= inicio_local.time() and fin_local.time() <= h.hora_fin:
                encaja = True
                break

        if not encaja:
            turnos_afectados.append(turno)

    if turnos_afectados:
        lista_turnos = [
            TurnoAfectadoOut(
                id_turno=t.id_turno,
                fecha_hora=t.fecha_hora,
                duracion_minutos=t.duracion_minutos,
                id_paciente=t.id_paciente,
            ).model_dump(mode="json")
            for t in turnos_afectados
        ]
        raise ApiError(
            409,
            "TURNOS_AFECTADOS_POR_HORARIO",
            "Turnos afectados por cambio de horario",
            "La modificación de horarios deja turnos ya reservados fuera del horario habilitado.",
            errors=lista_turnos,
        )

    # 3. Reemplazar horarios
    await session.execute(delete(HorarioMedico).where(HorarioMedico.id_medico == id_medico))

    nuevos_horarios: list[HorarioMedico] = []
    for h in horarios_ordenados:
        item = HorarioMedico(
            id_medico=id_medico,
            dia_semana=h.dia_semana,
            hora_inicio=h.hora_inicio,
            hora_fin=h.hora_fin,
            duracion_minutos=h.duracion_minutos,
            activo=h.activo,
        )
        session.add(item)
        nuevos_horarios.append(item)

    await session.flush()

    await auditoria_service.registrar(
        session,
        accion=Accion.MODIFICACION_HORARIOS_MEDICO,
        entidad="medico",
        entidad_id=id_medico,
        datos_despues={"cantidad_horarios": len(nuevos_horarios)},
        request=request,
        commit=False,
    )
    await session.commit()
    return [_salida_horario(h) for h in nuevos_horarios]


async def obtener_bloqueos(
    session: AsyncSession,
    id_medico: UUID,
    *,
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> list[BloqueoOut]:
    consulta = select(BloqueoAgenda).where(BloqueoAgenda.id_medico == id_medico)
    if desde is not None:
        consulta = consulta.where(BloqueoAgenda.fin >= desde)
    if hasta is not None:
        consulta = consulta.where(BloqueoAgenda.inicio <= hasta)

    bloqueos = (await session.scalars(consulta.order_by(BloqueoAgenda.inicio))).all()
    return [_salida_bloqueo(b) for b in bloqueos]


async def crear_bloqueo(
    session: AsyncSession,
    *,
    id_medico: UUID,
    payload: BloqueoCreate,
    usuario_creador: Usuario,
    request: Request,
) -> BloqueoOut:
    medico = await session.get(Medico, id_medico)
    if medico is None:
        raise ApiError(*MEDICO_NO_ENCONTRADO)

    if payload.fin <= payload.inicio:
        raise ApiError(
            400,
            "RANGO_INVALIDO",
            "Rango de fechas inválido",
            "La fecha/hora de fin debe ser posterior a la de inicio.",
        )

    # RF-26 / RN-38 / P-40: Detección de turnos afectados
    turnos_afectados = (
        await session.scalars(
            select(Turno)
            .where(
                Turno.id_medico == id_medico,
                Turno.estado.in_([EstadoTurno.RESERVADO, EstadoTurno.EN_ESPERA]),
                Turno.fecha_hora < payload.fin,
            )
            .order_by(Turno.fecha_hora)
        )
    ).all()

    # Filtro preciso: turno_inicio < bloqueo.fin AND turno_fin > bloqueo.inicio
    afectados_reales: list[Turno] = []
    for t in turnos_afectados:
        t_fin = t.fecha_hora + timedelta(minutes=t.duracion_minutos)
        if t.fecha_hora < payload.fin and t_fin > payload.inicio:
            afectados_reales.append(t)

    if afectados_reales:
        lista_turnos = [
            TurnoAfectadoOut(
                id_turno=t.id_turno,
                fecha_hora=t.fecha_hora,
                duracion_minutos=t.duracion_minutos,
                id_paciente=t.id_paciente,
            ).model_dump(mode="json")
            for t in afectados_reales
        ]
        raise ApiError(
            409,
            "TURNOS_AFECTADOS_POR_BLOQUEO",
            "Turnos afectados por el bloqueo",
            "No se puede confirmar el bloqueo porque se solapa con turnos ya reservados.",
            errors=lista_turnos,
        )

    bloqueo = BloqueoAgenda(
        id_medico=id_medico,
        inicio=payload.inicio,
        fin=payload.fin,
        motivo=payload.motivo.strip(),
        id_usuario_creador=usuario_creador.id_usuario,
    )
    session.add(bloqueo)
    await session.flush()

    await auditoria_service.registrar(
        session,
        accion=Accion.ALTA_BLOQUEO_AGENDA,
        entidad="bloqueo_agenda",
        entidad_id=bloqueo.id_bloqueo,
        datos_despues={
            "id_medico": str(id_medico),
            "inicio": bloqueo.inicio.isoformat(),
            "fin": bloqueo.fin.isoformat(),
            "motivo": bloqueo.motivo,
        },
        request=request,
        commit=False,
    )
    await session.commit()
    return _salida_bloqueo(bloqueo)


async def eliminar_bloqueo(
    session: AsyncSession,
    *,
    id_medico: UUID,
    id_bloqueo: UUID,
    request: Request,
) -> None:
    bloqueo = await session.scalar(
        select(BloqueoAgenda).where(
            BloqueoAgenda.id_bloqueo == id_bloqueo,
            BloqueoAgenda.id_medico == id_medico,
        )
    )
    if bloqueo is None:
        raise ApiError(*BLOQUEO_NO_ENCONTRADO)

    datos_antes = {
        "id_medico": str(id_medico),
        "inicio": bloqueo.inicio.isoformat(),
        "fin": bloqueo.fin.isoformat(),
        "motivo": bloqueo.motivo,
    }
    await session.delete(bloqueo)

    await auditoria_service.registrar(
        session,
        accion=Accion.BAJA_BLOQUEO_AGENDA,
        entidad="bloqueo_agenda",
        entidad_id=id_bloqueo,
        datos_antes=datos_antes,
        request=request,
        commit=False,
    )
    await session.commit()


async def calcular_disponibilidad(
    session: AsyncSession,
    *,
    id_medico: UUID,
    fecha_desde: date,
    fecha_hasta: date,
) -> DisponibilidadOut:
    if fecha_hasta < fecha_desde:
        raise ApiError(*RANGO_INVALIDO)

    dias_diferencia = (fecha_hasta - fecha_desde).days
    if dias_diferencia > settings.booking_horizon_days:
        raise ApiError(
            400,
            "HORIZONTE_EXCEDIDO",
            "Horizonte de reserva excedido",
            f"No se puede consultar disponibilidad a más de {settings.booking_horizon_days} días.",
        )

    medico = await session.get(Medico, id_medico)
    if medico is None or not medico.activo:
        return DisponibilidadOut(
            id_medico=id_medico,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            slots=[],
        )

    # 1. Obtener horarios habilitados
    horarios = (
        await session.scalars(
            select(HorarioMedico).where(
                HorarioMedico.id_medico == id_medico, HorarioMedico.activo.is_(True)
            )
        )
    ).all()

    if not horarios:
        return DisponibilidadOut(
            id_medico=id_medico,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            slots=[],
        )

    # 2. Rango en UTC
    inicio_utc = to_utc(datetime.combine(fecha_desde, time.min, tzinfo=LOCAL_TZ))
    fin_utc = to_utc(datetime.combine(fecha_hasta, time.max, tzinfo=LOCAL_TZ))

    # 3. Bloqueos y Turnos en el rango
    bloqueos = (
        await session.scalars(
            select(BloqueoAgenda).where(
                BloqueoAgenda.id_medico == id_medico,
                BloqueoAgenda.fin > inicio_utc,
                BloqueoAgenda.inicio < fin_utc,
            )
        )
    ).all()

    turnos_activos = (
        await session.scalars(
            select(Turno).where(
                Turno.id_medico == id_medico,
                Turno.estado.in_([EstadoTurno.RESERVADO, EstadoTurno.EN_ESPERA]),
                Turno.fecha_hora < fin_utc,
            )
        )
    ).all()

    ahora = now_utc()
    slots_disponibles: list[SlotDisponibilidad] = []

    # 4. Generación de slots día por día
    dia_actual = fecha_desde
    while dia_actual <= fecha_hasta:
        dia_semana = dia_actual.weekday()
        horarios_dia = [h for h in horarios if h.dia_semana == dia_semana]

        for h in horarios_dia:
            # Calcular cada slot dentro del bloque horario
            duracion = timedelta(minutes=h.duracion_minutos)
            slot_inicio_local = datetime.combine(dia_actual, h.hora_inicio, tzinfo=LOCAL_TZ)
            limite_local = datetime.combine(dia_actual, h.hora_fin, tzinfo=LOCAL_TZ)

            while slot_inicio_local + duracion <= limite_local:
                slot_fin_local = slot_inicio_local + duracion
                slot_inicio_utc = slot_inicio_local.astimezone(UTC)
                slot_fin_utc = slot_fin_local.astimezone(UTC)

                # Descartar si ya pasó
                if slot_inicio_utc > ahora:
                    # Descartar si choca con bloqueo
                    en_bloqueo = any(
                        b.inicio < slot_fin_utc and b.fin > slot_inicio_utc for b in bloqueos
                    )
                    # Descartar si choca con turno activo
                    en_turno = any(
                        t.fecha_hora < slot_fin_utc
                        and (t.fecha_hora + timedelta(minutes=t.duracion_minutos)) > slot_inicio_utc
                        for t in turnos_activos
                    )

                    if not en_bloqueo and not en_turno:
                        slots_disponibles.append(
                            SlotDisponibilidad(
                                fecha_hora=slot_inicio_utc,
                                duracion_minutos=h.duracion_minutos,
                            )
                        )

                slot_inicio_local += duracion

        dia_actual += timedelta(days=1)

    return DisponibilidadOut(
        id_medico=id_medico,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        slots=slots_disponibles,
    )


async def obtener_agenda(
    session: AsyncSession,
    *,
    id_medico: UUID,
    fecha_desde: date,
    fecha_hasta: date,
) -> AgendaOut:
    if fecha_hasta < fecha_desde:
        raise ApiError(*RANGO_INVALIDO)

    inicio_utc = to_utc(datetime.combine(fecha_desde, time.min, tzinfo=LOCAL_TZ))
    fin_utc = to_utc(datetime.combine(fecha_hasta, time.max, tzinfo=LOCAL_TZ))

    # Turnos con paciente
    filas_turnos = (
        await session.execute(
            select(Turno, Paciente, Usuario)
            .join(Paciente, Turno.id_paciente == Paciente.id_paciente)
            .join(Usuario, Paciente.id_usuario == Usuario.id_usuario)
            .where(
                Turno.id_medico == id_medico,
                Turno.fecha_hora >= inicio_utc,
                Turno.fecha_hora <= fin_utc,
            )
            .order_by(Turno.fecha_hora)
        )
    ).all()

    turnos_salida = [
        AgendaTurnoOut(
            id_turno=fila[0].id_turno,
            fecha_hora=fila[0].fecha_hora,
            duracion_minutos=fila[0].duracion_minutos,
            estado=fila[0].estado,
            id_paciente=fila[1].id_paciente,
            paciente_nombre=fila[2].nombre,
            paciente_apellido=fila[2].apellido,
            paciente_dni=fila[2].dni,
        )
        for fila in filas_turnos
    ]

    bloqueos = (
        await session.scalars(
            select(BloqueoAgenda)
            .where(
                BloqueoAgenda.id_medico == id_medico,
                BloqueoAgenda.fin >= inicio_utc,
                BloqueoAgenda.inicio <= fin_utc,
            )
            .order_by(BloqueoAgenda.inicio)
        )
    ).all()

    return AgendaOut(
        id_medico=id_medico,
        turnos=turnos_salida,
        bloqueos=[_salida_bloqueo(b) for b in bloqueos],
    )
