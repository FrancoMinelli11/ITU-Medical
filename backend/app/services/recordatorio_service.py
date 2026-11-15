"""Servicio de procesamiento de recordatorios de turnos 24 horas antes (RF-22, P-39)."""

from __future__ import annotations

from datetime import datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.timezone import now_utc, to_local
from app.db.models.enums import EstadoTurno, TipoNotificacion
from app.db.models.especialidad import Especialidad
from app.db.models.medico import Medico
from app.db.models.notificacion import Notificacion
from app.db.models.paciente import Paciente
from app.db.models.turno import Turno
from app.db.models.usuario import Usuario
from app.services import notificacion_service

logger = structlog.get_logger(__name__)


async def procesar_recordatorios_24h(
    session: AsyncSession,
    *,
    ahora: datetime | None = None,
) -> int:
    """Detecta turnos en RESERVADO a 24 horas y despacha el correo de recordatorio (RF-22, P-39).

    Idempotente: la base de datos restringe una única notificación RECORDATORIO_24H
    por turno (uq_notificacion_confirmacion_recordatorio).
    """
    tiempo_actual = ahora or now_utc()
    # Ventana de anticipación: turnos entre ahora y dentro de 24 horas y 30 minutos
    limite_superior = tiempo_actual + timedelta(hours=24, minutes=30)

    UsuarioPaciente = aliased(Usuario, name="usr_paciente")
    UsuarioMedico = aliased(Usuario, name="usr_medico")

    ya_notificado = (
        select(1)
        .where(
            Notificacion.id_turno == Turno.id_turno,
            Notificacion.tipo == TipoNotificacion.RECORDATORIO_24H,
        )
        .exists()
    )

    stmt = (
        select(Turno, Paciente, UsuarioPaciente, Medico, UsuarioMedico, Especialidad)
        .join(Paciente, Paciente.id_paciente == Turno.id_paciente)
        .join(UsuarioPaciente, UsuarioPaciente.id_usuario == Paciente.id_usuario)
        .join(Medico, Medico.id_medico == Turno.id_medico)
        .join(UsuarioMedico, UsuarioMedico.id_usuario == Medico.id_usuario)
        .join(Especialidad, Especialidad.id_especialidad == Medico.id_especialidad)
        .where(
            Turno.estado == EstadoTurno.RESERVADO,
            Turno.fecha_hora > tiempo_actual,
            Turno.fecha_hora <= limite_superior,
            ~ya_notificado,
        )
    )

    filas = (await session.execute(stmt)).all()
    despachados = 0

    for fila in filas:
        turno: Turno = fila[0]
        paciente_usr: Usuario = fila[2]
        medico_usr: Usuario = fila[4]
        especialidad: Especialidad = fila[5]

        try:
            notif = notificacion_service.crear(
                session,
                usuario=paciente_usr,
                tipo=TipoNotificacion.RECORDATORIO_24H,
                id_turno=turno.id_turno,
            )
            await session.commit()
        except IntegrityError:
            # Otra ejecución o worker ya creó la notificación (idempotencia garantizada)
            await session.rollback()
            continue

        fecha_local_str = to_local(turno.fecha_hora).strftime("%d/%m/%Y a las %H:%M hs")
        asunto, cuerpo = notificacion_service.cuerpo_recordatorio_24h(
            paciente_usr,
            fecha_hora_texto=fecha_local_str,
            medico_nombre_completo=f"Dr(a). {medico_usr.nombre} {medico_usr.apellido}",
            especialidad_nombre=especialidad.nombre,
        )

        ok = await notificacion_service.despachar(
            notif,
            destinatario=paciente_usr.email,
            asunto=asunto,
            cuerpo=cuerpo,
        )
        if ok:
            despachados += 1

    return despachados
