"""Gestión del ciclo de vida y reserva de turnos (RF-05, RF-06, RF-07, RF-25)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from starlette.requests import Request

from app.core.config import get_settings
from app.core.exceptions import ApiError
from app.core.rate_limit import RateLimiter, verificar_limites
from app.core.timezone import LOCAL_TZ, now_utc, to_local, to_utc
from app.db.models.bloqueo_agenda import BloqueoAgenda
from app.db.models.enums import EstadoTurno, RolUsuario, TipoNotificacion
from app.db.models.especialidad import Especialidad
from app.db.models.horario_medico import HorarioMedico
from app.db.models.medico import Medico
from app.db.models.paciente import Paciente
from app.db.models.restriccion_usuario import RestriccionUsuario
from app.db.models.turno import Turno
from app.db.models.usuario import Usuario
from app.schemas.turno import (
    ReservaTurnoRecepcionRequest,
    ReservaTurnoWebRequest,
    TurnoResponse,
    TurnosListResponse,
)
from app.services import auditoria_service, notificacion_service
from app.services.auditoria_service import Accion

settings = get_settings()

MEDICO_NO_ENCONTRADO = (
    404,
    "MEDICO_NO_ENCONTRADO",
    "Médico no encontrado",
    "El profesional médico no existe o no se encuentra habilitado.",
)
PACIENTE_NO_ENCONTRADO = (
    404,
    "PACIENTE_NO_ENCONTRADO",
    "Paciente no encontrado",
    "No se encontró el paciente indicado.",
)
TURNO_NO_ENCONTRADO = (
    404,
    "TURNO_NO_ENCONTRADO",
    "Turno no encontrado",
    "El turno solicitado no existe.",
)


async def es_usuario_rojo(session: AsyncSession, id_usuario: UUID) -> bool:
    """Verifica si el usuario tiene una restricción activa de Usuario rojo (RN-21, RN-36)."""
    ahora = now_utc()
    stmt = select(RestriccionUsuario).where(
        RestriccionUsuario.id_usuario == id_usuario,
        RestriccionUsuario.activa.is_(True),
        RestriccionUsuario.fecha_fin > ahora,
    )
    restriccion = await session.scalar(stmt)
    return restriccion is not None


def _validar_horario_agenda(horarios: list[HorarioMedico], fecha_inicio_utc: datetime) -> int:
    """Valida que la fecha/hora coincida con los bloques y duración de la agenda médica.

    Retorna la duración en minutos del turno correspondiente.
    """
    local_dt = to_local(fecha_inicio_utc)
    dia_semana = local_dt.weekday()
    hora_turno = local_dt.time()

    horarios_dia = [h for h in horarios if h.dia_semana == dia_semana and h.activo]
    if not horarios_dia:
        raise ApiError(
            400,
            "HORARIO_FUERA_DE_AGENDA",
            "Horario no disponible",
            "El profesional no atiende en el día seleccionado.",
        )

    for h in horarios_dia:
        if h.hora_inicio <= hora_turno:
            delta_minutos = timedelta(minutes=h.duracion_minutos)
            fin_turno_time = (datetime.combine(local_dt.date(), hora_turno) + delta_minutos).time()
            if fin_turno_time <= h.hora_fin:
                minutos_desde_inicio = (
                    hora_turno.hour * 60
                    + hora_turno.minute
                    - (h.hora_inicio.hour * 60 + h.hora_inicio.minute)
                )
                if minutos_desde_inicio % h.duracion_minutos == 0:
                    return h.duracion_minutos

    raise ApiError(
        400,
        "HORARIO_FUERA_DE_AGENDA",
        "Horario no disponible",
        "El horario seleccionado no coincide con los intervalos de atención del profesional.",
    )


async def _obtener_info_medico(
    session: AsyncSession, id_medico: UUID
) -> tuple[Medico, Usuario, Especialidad, list[HorarioMedico]]:
    medico = await session.get(Medico, id_medico)
    if medico is None or not medico.activo:
        raise ApiError(*MEDICO_NO_ENCONTRADO)

    medico_usuario = await session.get(Usuario, medico.id_usuario)
    if medico_usuario is None or not medico_usuario.habilitado:
        raise ApiError(*MEDICO_NO_ENCONTRADO)

    especialidad = await session.get(Especialidad, medico.id_especialidad)
    if especialidad is None or not especialidad.activa:
        raise ApiError(
            400,
            "ESPECIALIDAD_INACTIVA",
            "Especialidad no disponible",
            "La especialidad del médico no está disponible.",
        )

    horarios = (
        await session.scalars(
            select(HorarioMedico).where(
                HorarioMedico.id_medico == id_medico, HorarioMedico.activo.is_(True)
            )
        )
    ).all()

    return medico, medico_usuario, especialidad, list(horarios)


async def _validar_bloqueos(
    session: AsyncSession, id_medico: UUID, inicio_utc: datetime, fin_utc: datetime
) -> None:
    bloqueos = (
        await session.scalars(
            select(BloqueoAgenda).where(
                BloqueoAgenda.id_medico == id_medico,
                BloqueoAgenda.fin > inicio_utc,
                BloqueoAgenda.inicio < fin_utc,
            )
        )
    ).all()
    if bloqueos:
        raise ApiError(
            409,
            "HORARIO_BLOQUEADO",
            "Horario bloqueado",
            "El horario seleccionado se encuentra bloqueado en la agenda médica.",
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


async def reservar_web(
    session: AsyncSession,
    redis: Redis,
    *,
    usuario_paciente: Usuario,
    datos: ReservaTurnoWebRequest,
    request: Request | None = None,
) -> TurnoResponse:
    """Reserva de turno realizada por un paciente desde la web (RF-05, RF-06, RF-25, CU-03)."""
    # 1. Validar email verificado (P-32, RF-05)
    if not usuario_paciente.email_verificado:
        raise ApiError(
            403,
            "EMAIL_NO_VERIFICADO",
            "Correo no verificado",
            "Tenés que verificar tu correo electrónico para poder reservar turnos.",
        )

    # 2. Validar que no sea Usuario rojo (RN-21, P-25)
    if await es_usuario_rojo(session, usuario_paciente.id_usuario):
        raise ApiError(
            403,
            "USUARIO_ROJO_RESTRINGIDO",
            "Usuario restringido",
            "Tenés una restricción activa para reservar turnos por la web. "
            "Por favor solicitá tu turno en recepción.",
        )

    # 3. Rate limiting: 10 reservas por hora por paciente (RN-37)
    limiter = RateLimiter(redis, prefijo="booking:paciente", limite=settings.rate_limit_booking)
    await verificar_limites((limiter, str(usuario_paciente.id_usuario)))

    # 4. Obtener paciente
    paciente = await session.scalar(
        select(Paciente).where(Paciente.id_usuario == usuario_paciente.id_usuario)
    )
    if paciente is None:
        raise ApiError(*PACIENTE_NO_ENCONTRADO)

    # 5. Validar fecha en futuro y horizonte de reserva
    fecha_utc = to_utc(datos.fecha_hora)
    ahora = now_utc()
    if fecha_utc < ahora:
        raise ApiError(
            400,
            "FECHA_EN_PASADO",
            "Fecha inválida",
            "No se pueden reservar turnos en fechas o horarios pasados.",
        )

    dias_adelanto = (to_local(fecha_utc).date() - to_local(ahora).date()).days
    if dias_adelanto > settings.booking_horizon_days:
        raise ApiError(
            400,
            "HORIZONTE_EXCEDIDO",
            "Horizonte excedido",
            f"No se puede reservar con más de {settings.booking_horizon_days} días de "
            "anticipación.",
        )

    # 6. Validar médico y agenda
    medico, medico_usuario, especialidad, horarios = await _obtener_info_medico(
        session, datos.id_medico
    )
    duracion = _validar_horario_agenda(horarios, fecha_utc)
    fin_utc = fecha_utc + timedelta(minutes=duracion)

    # 7. Validar bloqueos de agenda
    await _validar_bloqueos(session, datos.id_medico, fecha_utc, fin_utc)

    # 8. Insertar Turno con manejo de concurrencia y exclusion constraints
    turno = Turno(
        id_paciente=paciente.id_paciente,
        id_medico=medico.id_medico,
        fecha_hora=fecha_utc,
        duracion_minutos=duracion,
        estado=EstadoTurno.RESERVADO,
        id_usuario_creador=usuario_paciente.id_usuario,
    )
    session.add(turno)

    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        error_msg = str(exc)
        if "ex_turno_medico" in error_msg:
            raise ApiError(
                409,
                "TURNO_OCUPADO",
                "Horario no disponible",
                "El profesional ya tiene un turno reservado en ese horario.",
            ) from exc
        if "ex_turno_paciente" in error_msg:
            raise ApiError(
                409,
                "TURNO_SOLAPADO_PACIENTE",
                "Turno superpuesto",
                "Ya tenés otro turno reservado en ese mismo horario.",
            ) from exc
        raise ApiError(
            409,
            "CONFLICTO_TURNO",
            "Conflicto de reserva",
            "No se pudo concretar la reserva debido a un conflicto de agenda.",
        ) from exc

    # 9. Notificación de confirmación de turno (RF-22, RN-32, P-42)
    notificacion = notificacion_service.crear(
        session,
        usuario=usuario_paciente,
        tipo=TipoNotificacion.CONFIRMACION_TURNO,
        id_turno=turno.id_turno,
    )

    # 10. Auditoría (RF-19)
    await auditoria_service.registrar(
        session,
        accion=Accion.RESERVA_TURNO_WEB,
        id_usuario=usuario_paciente.id_usuario,
        entidad="turno",
        entidad_id=turno.id_turno,
        request=request,
    )

    # Confirmar la transacción
    await session.commit()
    await limiter.registrar(str(usuario_paciente.id_usuario))

    # Despachar correo asíncronamente
    fecha_texto = to_local(fecha_utc).strftime("%d/%m/%Y a las %H:%M hs")
    medico_texto = f"{medico_usuario.nombre} {medico_usuario.apellido}"
    asunto, cuerpo = notificacion_service.cuerpo_confirmacion_turno(
        usuario_paciente,
        fecha_hora_texto=fecha_texto,
        medico_nombre_completo=medico_texto,
        especialidad_nombre=especialidad.nombre,
    )
    await notificacion_service.despachar(
        notificacion, destinatario=usuario_paciente.email, asunto=asunto, cuerpo=cuerpo
    )

    return _armar_turno_response(turno, medico_usuario, especialidad, usuario_paciente)


async def reservar_recepcion(
    session: AsyncSession,
    *,
    usuario_staff: Usuario,
    datos: ReservaTurnoRecepcionRequest,
    request: Request | None = None,
) -> TurnoResponse:
    """Reserva de turno realizada por el personal de recepción (RF-07, CU-04)."""
    # 1. Obtener el paciente (por ID o por DNI)
    if datos.id_paciente is not None:
        paciente = await session.get(Paciente, datos.id_paciente)
    elif datos.dni_paciente is not None:
        paciente = await session.scalar(
            select(Paciente)
            .join(Usuario, Usuario.id_usuario == Paciente.id_usuario)
            .where(Usuario.dni == datos.dni_paciente)
        )
    else:
        raise ApiError(
            400,
            "PACIENTE_REQUERIDO",
            "Paciente no especificado",
            "Debés indicar el id_paciente o el dni_paciente.",
        )

    if paciente is None:
        raise ApiError(*PACIENTE_NO_ENCONTRADO)

    paciente_usuario = await session.get(Usuario, paciente.id_usuario)
    if paciente_usuario is None:
        raise ApiError(*PACIENTE_NO_ENCONTRADO)

    # 2. Validar fecha y horizonte
    fecha_utc = to_utc(datos.fecha_hora)
    ahora = now_utc()
    if fecha_utc < ahora:
        raise ApiError(
            400,
            "FECHA_EN_PASADO",
            "Fecha inválida",
            "No se pueden reservar turnos en fechas o horarios pasados.",
        )

    # 3. Validar médico y agenda
    medico, medico_usuario, especialidad, horarios = await _obtener_info_medico(
        session, datos.id_medico
    )
    duracion = _validar_horario_agenda(horarios, fecha_utc)
    fin_utc = fecha_utc + timedelta(minutes=duracion)

    # 4. Validar bloqueos
    await _validar_bloqueos(session, datos.id_medico, fecha_utc, fin_utc)

    # 5. Insertar Turno con exclusion constraints
    turno = Turno(
        id_paciente=paciente.id_paciente,
        id_medico=medico.id_medico,
        fecha_hora=fecha_utc,
        duracion_minutos=duracion,
        estado=EstadoTurno.RESERVADO,
        id_usuario_creador=usuario_staff.id_usuario,
    )
    session.add(turno)

    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        error_msg = str(exc)
        if "ex_turno_medico" in error_msg:
            raise ApiError(
                409,
                "TURNO_OCUPADO",
                "Horario no disponible",
                "El profesional ya tiene un turno reservado en ese horario.",
            ) from exc
        if "ex_turno_paciente" in error_msg:
            raise ApiError(
                409,
                "TURNO_SOLAPADO_PACIENTE",
                "Turno superpuesto",
                "El paciente ya tiene otro turno reservado en ese mismo horario.",
            ) from exc
        raise ApiError(
            409,
            "CONFLICTO_TURNO",
            "Conflicto de reserva",
            "No se pudo concretar la reserva debido a un conflicto de agenda.",
        ) from exc

    # 6. Notificación de confirmación de turno (RF-22)
    notificacion = notificacion_service.crear(
        session,
        usuario=paciente_usuario,
        tipo=TipoNotificacion.CONFIRMACION_TURNO,
        id_turno=turno.id_turno,
    )

    # 7. Auditoría
    await auditoria_service.registrar(
        session,
        accion=Accion.RESERVA_TURNO_RECEPCION,
        id_usuario=usuario_staff.id_usuario,
        entidad="turno",
        entidad_id=turno.id_turno,
        request=request,
    )

    await session.commit()

    # Despachar correo asíncronamente
    fecha_texto = to_local(fecha_utc).strftime("%d/%m/%Y a las %H:%M hs")
    medico_texto = f"{medico_usuario.nombre} {medico_usuario.apellido}"
    asunto, cuerpo = notificacion_service.cuerpo_confirmacion_turno(
        paciente_usuario,
        fecha_hora_texto=fecha_texto,
        medico_nombre_completo=medico_texto,
        especialidad_nombre=especialidad.nombre,
    )
    await notificacion_service.despachar(
        notificacion, destinatario=paciente_usuario.email, asunto=asunto, cuerpo=cuerpo
    )

    return _armar_turno_response(turno, medico_usuario, especialidad, paciente_usuario)


async def listar_turnos(
    session: AsyncSession,
    *,
    usuario_actual: Usuario,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    estado: EstadoTurno | None = None,
    id_medico: UUID | None = None,
    id_paciente: UUID | None = None,
    pagina: int = 1,
    tamano_pagina: int = 20,
) -> TurnosListResponse:
    """Lista turnos con control de permisos por rol (RNF-03)."""
    filtros = []

    # Filtrar según el rol del usuario autenticado
    if usuario_actual.rol == RolUsuario.PACIENTE:
        paciente = await session.scalar(
            select(Paciente).where(Paciente.id_usuario == usuario_actual.id_usuario)
        )
        if paciente is None:
            return TurnosListResponse(items=[], total=0, pagina=pagina, tamano_pagina=tamano_pagina)
        filtros.append(Turno.id_paciente == paciente.id_paciente)

    elif usuario_actual.rol == RolUsuario.MEDICO:
        medico = await session.scalar(
            select(Medico).where(Medico.id_usuario == usuario_actual.id_usuario)
        )
        if medico is None:
            return TurnosListResponse(items=[], total=0, pagina=pagina, tamano_pagina=tamano_pagina)
        filtros.append(Turno.id_medico == medico.id_medico)

    else:
        # RECEPCIONISTA o ADMINISTRADOR pueden filtrar opcionalmente
        if id_paciente is not None:
            filtros.append(Turno.id_paciente == id_paciente)
        if id_medico is not None:
            filtros.append(Turno.id_medico == id_medico)

    if estado is not None:
        filtros.append(Turno.estado == estado)

    if fecha_desde is not None:
        inicio_utc = to_utc(datetime.combine(fecha_desde, time.min, tzinfo=LOCAL_TZ))
        filtros.append(Turno.fecha_hora >= inicio_utc)

    if fecha_hasta is not None:
        fin_utc = to_utc(datetime.combine(fecha_hasta, time.max, tzinfo=LOCAL_TZ))
        filtros.append(Turno.fecha_hora <= fin_utc)

    # Total de registros sin joins innecesarios
    count_stmt = select(func.count(Turno.id_turno)).where(*filtros)
    total = (await session.scalar(count_stmt)) or 0

    # Aliases separados para evitar el error 'table name "usuario" specified more than once'
    UsuarioMedico = aliased(Usuario, name="usuario_medico")
    UsuarioPaciente = aliased(Usuario, name="usuario_paciente")

    stmt = (
        select(Turno, Medico, UsuarioMedico, Especialidad, Paciente, UsuarioPaciente)
        .join(Medico, Medico.id_medico == Turno.id_medico)
        .join(UsuarioMedico, UsuarioMedico.id_usuario == Medico.id_usuario)
        .join(Especialidad, Especialidad.id_especialidad == Medico.id_especialidad)
        .join(Paciente, Paciente.id_paciente == Turno.id_paciente)
        .join(UsuarioPaciente, UsuarioPaciente.id_usuario == Paciente.id_usuario)
        .where(*filtros)
        .order_by(Turno.fecha_hora.asc())
        .offset((pagina - 1) * tamano_pagina)
        .limit(tamano_pagina)
    )

    resultados = (await session.execute(stmt)).all()
    items: list[TurnoResponse] = []
    for fila in resultados:
        turno = fila[0]
        medico_usuario = fila[2]
        especialidad = fila[3]
        paciente_usuario = fila[5]
        items.append(_armar_turno_response(turno, medico_usuario, especialidad, paciente_usuario))

    return TurnosListResponse(
        items=items,
        total=total,
        pagina=pagina,
        tamano_pagina=tamano_pagina,
    )


async def obtener_turno(
    session: AsyncSession, *, id_turno: UUID, usuario_actual: Usuario
) -> TurnoResponse:
    """Obtiene el detalle de un turno verificando permisos (RNF-03)."""
    turno = await session.get(Turno, id_turno)
    if turno is None:
        raise ApiError(*TURNO_NO_ENCONTRADO)

    medico = await session.get(Medico, turno.id_medico)
    paciente = await session.get(Paciente, turno.id_paciente)
    if medico is None or paciente is None:
        raise ApiError(*TURNO_NO_ENCONTRADO)

    # Validar permisos
    if usuario_actual.rol == RolUsuario.PACIENTE:
        if paciente.id_usuario != usuario_actual.id_usuario:
            raise ApiError(
                403,
                "ACCESO_DENEGADO",
                "Permisos insuficientes",
                "No podés ver turnos de otros pacientes.",
            )
    elif usuario_actual.rol == RolUsuario.MEDICO:
        if medico.id_usuario != usuario_actual.id_usuario:
            raise ApiError(
                403,
                "ACCESO_DENEGADO",
                "Permisos insuficientes",
                "No podés ver turnos de otros profesionales.",
            )

    medico_usuario = await session.get(Usuario, medico.id_usuario)
    especialidad = await session.get(Especialidad, medico.id_especialidad)
    paciente_usuario = await session.get(Usuario, paciente.id_usuario)
    assert medico_usuario and especialidad and paciente_usuario

    return _armar_turno_response(turno, medico_usuario, especialidad, paciente_usuario)
