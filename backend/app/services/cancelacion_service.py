"""Lógica de cancelaciones habituales, solicitudes y resolución (RF-08, RF-09, RF-10, RF-24)."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from starlette.requests import Request

from app.core.exceptions import ApiError
from app.core.timezone import now_utc, to_local
from app.db.models.enums import (
    EstadoSolicitudCancelacion,
    EstadoTurno,
    MotivoCancelacion,
    RolUsuario,
    TipoNotificacion,
)
from app.db.models.especialidad import Especialidad
from app.db.models.medico import Medico
from app.db.models.paciente import Paciente
from app.db.models.solicitud_cancelacion import SolicitudCancelacion
from app.db.models.turno import Turno
from app.db.models.usuario import Usuario
from app.schemas.cancelacion import (
    CancelacionPacienteRequest,
    CancelacionRecepcionRequest,
    ResolucionSolicitudRequest,
    SolicitudCancelacionCreate,
    SolicitudCancelacionOut,
)
from app.schemas.turno import TurnoResponse
from app.services import auditoria_service, notificacion_service
from app.services.auditoria_service import Accion

TURNO_NO_ENCONTRADO = (
    404,
    "TURNO_NO_ENCONTRADO",
    "Turno no encontrado",
    "El turno solicitado no existe.",
)
SOLICITUD_NO_ENCONTRADA = (
    404,
    "SOLICITUD_NO_ENCONTRADA",
    "Solicitud no encontrada",
    "La solicitud de cancelación no existe.",
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


async def cancelar_turno_paciente(
    session: AsyncSession,
    *,
    id_turno: UUID,
    usuario_paciente: Usuario,
    datos: CancelacionPacienteRequest | None = None,
    request: Request | None = None,
) -> TurnoResponse:
    """Cancelación habitual de turno por parte del paciente (RF-08, CU-05, P-12)."""
    turno = await session.get(Turno, id_turno)
    if turno is None:
        raise ApiError(*TURNO_NO_ENCONTRADO)

    paciente = await session.scalar(
        select(Paciente).where(Paciente.id_usuario == usuario_paciente.id_usuario)
    )
    if paciente is None or turno.id_paciente != paciente.id_paciente:
        raise ApiError(
            403,
            "ACCESO_DENEGADO",
            "Permisos insuficientes",
            "No podés cancelar un turno que no te pertenece.",
        )

    if turno.estado != EstadoTurno.RESERVADO:
        raise ApiError(
            400,
            "TRANSICION_INVALIDA",
            "Transición no permitida",
            f"No se puede cancelar un turno en estado {turno.estado.value}.",
        )

    ahora = now_utc()
    if turno.fecha_hora - ahora < timedelta(hours=24):
        raise ApiError(
            400,
            "PLAZO_CANCELACION_EXCEDIDO",
            "Cancelación habitual no permitida",
            "Faltan menos de 24 horas para el turno. Debés solicitar una cancelación rápida.",
        )

    turno.estado = EstadoTurno.CANCELADO
    turno.fecha_hora_cancelacion = ahora
    turno.motivo_cancelacion = MotivoCancelacion.HABITUAL
    turno.detalle_cancelacion = datos.motivo if datos else None
    turno.id_usuario_cancelacion = usuario_paciente.id_usuario

    # Obtener médico y especialidad para armar notificación y respuesta
    medico = await session.get(Medico, turno.id_medico)
    assert medico is not None
    medico_usuario = await session.get(Usuario, medico.id_usuario)
    especialidad = await session.get(Especialidad, medico.id_especialidad)
    assert medico_usuario and especialidad

    notificacion = notificacion_service.crear(
        session,
        usuario=usuario_paciente,
        tipo=TipoNotificacion.CANCELACION_TURNO,
        id_turno=turno.id_turno,
        subtipo="HABITUAL",
    )

    await auditoria_service.registrar(
        session,
        accion=Accion.CANCELACION_TURNO_PACIENTE,
        id_usuario=usuario_paciente.id_usuario,
        entidad="turno",
        entidad_id=turno.id_turno,
        request=request,
    )

    await session.commit()

    fecha_texto = to_local(turno.fecha_hora).strftime("%d/%m/%Y a las %H:%M hs")
    medico_texto = f"{medico_usuario.nombre} {medico_usuario.apellido}"
    asunto, cuerpo = notificacion_service.cuerpo_cancelacion_turno(
        usuario_paciente,
        fecha_hora_texto=fecha_texto,
        medico_nombre_completo=medico_texto,
        especialidad_nombre=especialidad.nombre,
        motivo_texto="Cancelación voluntaria habitual",
        aprobada=True,
    )
    await notificacion_service.despachar(
        notificacion, destinatario=usuario_paciente.email, asunto=asunto, cuerpo=cuerpo
    )

    return _armar_turno_response(turno, medico_usuario, especialidad, usuario_paciente)


async def solicitar_cancelacion_rapida(
    session: AsyncSession,
    *,
    id_turno: UUID,
    usuario_paciente: Usuario,
    datos: SolicitudCancelacionCreate,
    request: Request | None = None,
) -> SolicitudCancelacionOut:
    """Crea una solicitud de cancelación rápida para un turno próximo (RF-09, CU-06, P-13, P-14)."""
    turno = await session.get(Turno, id_turno)
    if turno is None:
        raise ApiError(*TURNO_NO_ENCONTRADO)

    paciente = await session.scalar(
        select(Paciente).where(Paciente.id_usuario == usuario_paciente.id_usuario)
    )
    if paciente is None or turno.id_paciente != paciente.id_paciente:
        raise ApiError(
            403,
            "ACCESO_DENEGADO",
            "Permisos insuficientes",
            "No podés solicitar la cancelación de un turno ajeno.",
        )

    if turno.estado != EstadoTurno.RESERVADO:
        raise ApiError(
            400,
            "TRANSICION_INVALIDA",
            "Transición no permitida",
            f"No se puede solicitar cancelación para un turno en estado {turno.estado.value}.",
        )

    ahora = now_utc()
    if turno.fecha_hora < ahora:
        raise ApiError(
            400,
            "TURNO_PASADO",
            "Turno ya transcurrido",
            "No se puede solicitar cancelación para un turno que ya pasó.",
        )

    # Verificar que no exista solicitud pendiente para este turno
    solicitud_existente = await session.scalar(
        select(SolicitudCancelacion).where(
            SolicitudCancelacion.id_turno == turno.id_turno,
            SolicitudCancelacion.estado == EstadoSolicitudCancelacion.PENDIENTE,
        )
    )
    if solicitud_existente is not None:
        raise ApiError(
            409,
            "SOLICITUD_PENDIENTE_EXISTENTE",
            "Solicitud pendiente en curso",
            "Ya existe una solicitud de cancelación pendiente para este turno.",
        )

    solicitud = SolicitudCancelacion(
        id_turno=turno.id_turno,
        id_paciente=paciente.id_paciente,
        motivo=datos.motivo,
        estado=EstadoSolicitudCancelacion.PENDIENTE,
    )
    session.add(solicitud)
    await session.flush()

    await auditoria_service.registrar(
        session,
        accion=Accion.ALTA_SOLICITUD_CANCELACION,
        id_usuario=usuario_paciente.id_usuario,
        entidad="solicitud_cancelacion",
        entidad_id=solicitud.id_solicitud,
        request=request,
    )

    await session.commit()

    medico = await session.get(Medico, turno.id_medico)
    assert medico is not None
    medico_usuario = await session.get(Usuario, medico.id_usuario)
    especialidad = await session.get(Especialidad, medico.id_especialidad)

    return SolicitudCancelacionOut(
        id_solicitud=solicitud.id_solicitud,
        id_turno=solicitud.id_turno,
        id_paciente=solicitud.id_paciente,
        motivo=solicitud.motivo,
        estado=solicitud.estado,
        id_usuario_resolucion=solicitud.id_usuario_resolucion,
        fecha_resolucion=solicitud.fecha_resolucion,
        detalle_resolucion=solicitud.detalle_resolucion,
        fecha_creacion=solicitud.fecha_creacion,
        paciente_nombre=usuario_paciente.nombre,
        paciente_apellido=usuario_paciente.apellido,
        paciente_dni=usuario_paciente.dni,
        turno_fecha_hora=turno.fecha_hora,
        medico_nombre=medico_usuario.nombre if medico_usuario else None,
        medico_apellido=medico_usuario.apellido if medico_usuario else None,
        especialidad_nombre=especialidad.nombre if especialidad else None,
    )


async def cancelar_turno_recepcion(
    session: AsyncSession,
    *,
    id_turno: UUID,
    usuario_staff: Usuario,
    datos: CancelacionRecepcionRequest,
    request: Request | None = None,
) -> TurnoResponse:
    """Cancelación administrativa de turno por parte de recepción o admin (RF-10, RF-24, P-16)."""
    turno = await session.get(Turno, id_turno)
    if turno is None:
        raise ApiError(*TURNO_NO_ENCONTRADO)

    if turno.estado not in (EstadoTurno.RESERVADO, EstadoTurno.EN_ESPERA):
        raise ApiError(
            400,
            "TRANSICION_INVALIDA",
            "Transición no permitida",
            f"No se puede cancelar un turno en estado {turno.estado.value}.",
        )

    ahora = now_utc()
    turno.estado = EstadoTurno.CANCELADO
    turno.fecha_hora_cancelacion = ahora
    turno.motivo_cancelacion = datos.motivo
    turno.detalle_cancelacion = datos.detalle
    turno.id_usuario_cancelacion = usuario_staff.id_usuario

    # Si había una solicitud pendiente, marcarla resuelta
    solicitud = await session.scalar(
        select(SolicitudCancelacion).where(
            SolicitudCancelacion.id_turno == turno.id_turno,
            SolicitudCancelacion.estado == EstadoSolicitudCancelacion.PENDIENTE,
        )
    )
    if solicitud is not None:
        solicitud.estado = EstadoSolicitudCancelacion.APROBADA
        solicitud.id_usuario_resolucion = usuario_staff.id_usuario
        solicitud.fecha_resolucion = ahora
        solicitud.detalle_resolucion = datos.detalle or "Cancelado desde recepción"

    paciente = await session.get(Paciente, turno.id_paciente)
    assert paciente is not None
    paciente_usuario = await session.get(Usuario, paciente.id_usuario)
    assert paciente_usuario is not None

    medico = await session.get(Medico, turno.id_medico)
    assert medico is not None
    medico_usuario = await session.get(Usuario, medico.id_usuario)
    especialidad = await session.get(Especialidad, medico.id_especialidad)
    assert medico_usuario and especialidad

    notificacion = notificacion_service.crear(
        session,
        usuario=paciente_usuario,
        tipo=TipoNotificacion.CANCELACION_TURNO,
        id_turno=turno.id_turno,
        subtipo=datos.motivo.value,
    )

    await auditoria_service.registrar(
        session,
        accion=Accion.CANCELACION_TURNO_RECEPCION,
        id_usuario=usuario_staff.id_usuario,
        entidad="turno",
        entidad_id=turno.id_turno,
        request=request,
    )

    await session.commit()

    fecha_texto = to_local(turno.fecha_hora).strftime("%d/%m/%Y a las %H:%M hs")
    medico_texto = f"{medico_usuario.nombre} {medico_usuario.apellido}"
    asunto, cuerpo = notificacion_service.cuerpo_cancelacion_turno(
        paciente_usuario,
        fecha_hora_texto=fecha_texto,
        medico_nombre_completo=medico_texto,
        especialidad_nombre=especialidad.nombre,
        motivo_texto=f"{datos.motivo.value}: {datos.detalle or 'Cancelado por el centro médico'}",
        aprobada=True,
    )
    await notificacion_service.despachar(
        notificacion, destinatario=paciente_usuario.email, asunto=asunto, cuerpo=cuerpo
    )

    return _armar_turno_response(turno, medico_usuario, especialidad, paciente_usuario)


async def resolver_solicitud_cancelacion(
    session: AsyncSession,
    *,
    id_solicitud: UUID,
    usuario_staff: Usuario,
    datos: ResolucionSolicitudRequest,
    request: Request | None = None,
) -> SolicitudCancelacionOut:
    """Aprobación o rechazo de solicitud de cancelación rápida por recepción (RF-09, P-15)."""
    solicitud = await session.get(SolicitudCancelacion, id_solicitud)
    if solicitud is None:
        raise ApiError(*SOLICITUD_NO_ENCONTRADA)

    if solicitud.estado != EstadoSolicitudCancelacion.PENDIENTE:
        raise ApiError(
            400,
            "SOLICITUD_YA_RESUELTA",
            "Solicitud ya procesada",
            f"La solicitud ya se encuentra en estado {solicitud.estado.value}.",
        )

    turno = await session.get(Turno, solicitud.id_turno)
    assert turno is not None

    paciente = await session.get(Paciente, turno.id_paciente)
    assert paciente is not None
    paciente_usuario = await session.get(Usuario, paciente.id_usuario)
    assert paciente_usuario is not None

    medico = await session.get(Medico, turno.id_medico)
    assert medico is not None
    medico_usuario = await session.get(Usuario, medico.id_usuario)
    especialidad = await session.get(Especialidad, medico.id_especialidad)
    assert medico_usuario and especialidad

    ahora = now_utc()
    solicitud.id_usuario_resolucion = usuario_staff.id_usuario
    solicitud.fecha_resolucion = ahora
    solicitud.detalle_resolucion = datos.detalle

    if datos.aprobada:
        solicitud.estado = EstadoSolicitudCancelacion.APROBADA
        turno.estado = EstadoTurno.CANCELADO
        turno.fecha_hora_cancelacion = ahora
        turno.motivo_cancelacion = MotivoCancelacion.RAPIDA
        turno.detalle_cancelacion = datos.detalle or solicitud.motivo
        turno.id_usuario_cancelacion = usuario_staff.id_usuario
        subtipo = "RAPIDA_APROBADA"
    else:
        solicitud.estado = EstadoSolicitudCancelacion.RECHAZADA
        # El turno conserva su estado RESERVADO
        subtipo = "RAPIDA_RECHAZADA"

    notificacion = notificacion_service.crear(
        session,
        usuario=paciente_usuario,
        tipo=TipoNotificacion.CANCELACION_TURNO,
        id_turno=turno.id_turno,
        subtipo=subtipo,
    )

    await auditoria_service.registrar(
        session,
        accion=Accion.RESOLUCION_SOLICITUD_CANCELACION,
        id_usuario=usuario_staff.id_usuario,
        entidad="solicitud_cancelacion",
        entidad_id=solicitud.id_solicitud,
        request=request,
    )

    await session.commit()

    fecha_texto = to_local(turno.fecha_hora).strftime("%d/%m/%Y a las %H:%M hs")
    medico_texto = f"{medico_usuario.nombre} {medico_usuario.apellido}"
    texto_motivo = datos.detalle or (
        "Solicitud aprobada" if datos.aprobada else "No cumple criterios"
    )
    asunto, cuerpo = notificacion_service.cuerpo_cancelacion_turno(
        paciente_usuario,
        fecha_hora_texto=fecha_texto,
        medico_nombre_completo=medico_texto,
        especialidad_nombre=especialidad.nombre,
        motivo_texto=texto_motivo,
        aprobada=datos.aprobada,
    )
    await notificacion_service.despachar(
        notificacion, destinatario=paciente_usuario.email, asunto=asunto, cuerpo=cuerpo
    )

    return SolicitudCancelacionOut(
        id_solicitud=solicitud.id_solicitud,
        id_turno=solicitud.id_turno,
        id_paciente=solicitud.id_paciente,
        motivo=solicitud.motivo,
        estado=solicitud.estado,
        id_usuario_resolucion=solicitud.id_usuario_resolucion,
        fecha_resolucion=solicitud.fecha_resolucion,
        detalle_resolucion=solicitud.detalle_resolucion,
        fecha_creacion=solicitud.fecha_creacion,
        paciente_nombre=paciente_usuario.nombre,
        paciente_apellido=paciente_usuario.apellido,
        paciente_dni=paciente_usuario.dni,
        turno_fecha_hora=turno.fecha_hora,
        medico_nombre=medico_usuario.nombre,
        medico_apellido=medico_usuario.apellido,
        especialidad_nombre=especialidad.nombre,
    )


async def listar_solicitudes_cancelacion(
    session: AsyncSession,
    *,
    usuario_actual: Usuario,
    estado: EstadoSolicitudCancelacion | None = None,
) -> list[SolicitudCancelacionOut]:
    """Lista las solicitudes de cancelación para recepción o para el paciente actual."""
    UsuarioMedico = aliased(Usuario, name="usuario_medico")
    UsuarioPaciente = aliased(Usuario, name="usuario_paciente")

    stmt = (
        select(
            SolicitudCancelacion,
            Turno,
            Medico,
            UsuarioMedico,
            Especialidad,
            Paciente,
            UsuarioPaciente,
        )
        .join(Turno, Turno.id_turno == SolicitudCancelacion.id_turno)
        .join(Medico, Medico.id_medico == Turno.id_medico)
        .join(UsuarioMedico, UsuarioMedico.id_usuario == Medico.id_usuario)
        .join(Especialidad, Especialidad.id_especialidad == Medico.id_especialidad)
        .join(Paciente, Paciente.id_paciente == SolicitudCancelacion.id_paciente)
        .join(UsuarioPaciente, UsuarioPaciente.id_usuario == Paciente.id_usuario)
    )

    if usuario_actual.rol == RolUsuario.PACIENTE:
        paciente = await session.scalar(
            select(Paciente).where(Paciente.id_usuario == usuario_actual.id_usuario)
        )
        if paciente is None:
            return []
        stmt = stmt.where(SolicitudCancelacion.id_paciente == paciente.id_paciente)

    if estado is not None:
        stmt = stmt.where(SolicitudCancelacion.estado == estado)

    stmt = stmt.order_by(SolicitudCancelacion.fecha_creacion.desc())
    filas = (await session.execute(stmt)).all()

    items: list[SolicitudCancelacionOut] = []
    for f in filas:
        solicitud = f[0]
        turno = f[1]
        medico_usuario = f[3]
        especialidad = f[4]
        paciente_usuario = f[6]
        items.append(
            SolicitudCancelacionOut(
                id_solicitud=solicitud.id_solicitud,
                id_turno=solicitud.id_turno,
                id_paciente=solicitud.id_paciente,
                motivo=solicitud.motivo,
                estado=solicitud.estado,
                id_usuario_resolucion=solicitud.id_usuario_resolucion,
                fecha_resolucion=solicitud.fecha_resolucion,
                detalle_resolucion=solicitud.detalle_resolucion,
                fecha_creacion=solicitud.fecha_creacion,
                paciente_nombre=paciente_usuario.nombre,
                paciente_apellido=paciente_usuario.apellido,
                paciente_dni=paciente_usuario.dni,
                turno_fecha_hora=turno.fecha_hora,
                medico_nombre=medico_usuario.nombre,
                medico_apellido=medico_usuario.apellido,
                especialidad_nombre=especialidad.nombre,
            )
        )
    return items
