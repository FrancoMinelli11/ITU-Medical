"""Pruebas del scheduler de recordatorios 24 hs (RF-22, P-39).

Cubre:
- P-39: Detección de turnos a 24 horas y despacho de recordatorio.
- Idempotencia garantizada por base de datos (uq_notificacion_confirmacion_recordatorio).
- Exclusión de turnos cancelados, pasados o fuera de la ventana.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.core.timezone import now_utc
from app.db.models.enums import EstadoTurno, RolUsuario, TipoNotificacion
from app.db.models.especialidad import Especialidad
from app.db.models.medico import Medico
from app.db.models.notificacion import Notificacion
from app.db.models.paciente import Paciente
from app.db.models.turno import Turno
from app.db.session import SessionLocal
from app.services.recordatorio_service import procesar_recordatorios_24h

PASSWORD = "Password123!"


async def _crear_entorno_turno(
    fabrica: Any,
    *,
    delta_horas: float = 24.0,
    estado: EstadoTurno = EstadoTurno.RESERVADO,
) -> tuple[Turno, Paciente, Any]:
    """Crea paciente, médico, especialidad y un turno con el delta de horas y estado indicados."""
    async with SessionLocal() as db:
        esp = Especialidad(nombre=f"Esp-{uuid4().hex[:8]}")
        db.add(esp)
        await db.flush()

        med_usr = await fabrica.crear(
            rol=RolUsuario.MEDICO,
            password=PASSWORD,
            email=f"med-{uuid4().hex[:6]}@example.com",
            nombre="Carlos",
            apellido="Gómez",
        )
        medico = Medico(
            id_usuario=med_usr.id_usuario,
            id_especialidad=esp.id_especialidad,
            matricula=f"MN-{uuid4().hex[:6]}",
            activo=True,
        )
        db.add(medico)

        pac_usr = await fabrica.crear(
            rol=RolUsuario.PACIENTE,
            password=PASSWORD,
            email_verificado=True,
            nombre="Ana",
            apellido="Pérez",
        )
        paciente = await db.scalar(
            select(Paciente).where(Paciente.id_usuario == pac_usr.id_usuario)
        )
        assert paciente is not None

        fecha_turno = now_utc() + timedelta(hours=delta_horas)
        turno = Turno(
            id_paciente=paciente.id_paciente,
            id_medico=medico.id_medico,
            fecha_hora=fecha_turno,
            duracion_minutos=30,
            estado=estado,
            id_usuario_creador=pac_usr.id_usuario,
        )
        db.add(turno)
        await db.commit()
        await db.refresh(turno)

        return turno, paciente, pac_usr


async def test_envio_recordatorio_24hs_ok(fabrica: Any, buzon: Any) -> None:
    """P-39: El scheduler detecta turno a 24 horas y envía el recordatorio."""
    turno, _, pac_usr = await _crear_entorno_turno(fabrica, delta_horas=24.0)

    async with SessionLocal() as db:
        total = await procesar_recordatorios_24h(db)
        assert total == 1

        # Verificar fila en notificacion
        notif = await db.scalar(
            select(Notificacion).where(
                Notificacion.id_turno == turno.id_turno,
                Notificacion.tipo == TipoNotificacion.RECORDATORIO_24H,
            )
        )
        assert notif is not None
        assert notif.id_usuario_destinatario == pac_usr.id_usuario

    # Verificar despacho de correo en buzón
    envios = buzon.de(pac_usr.email)
    assert len(envios) == 1
    assert "Recordatorio de turno médico mañana" in envios[0]["asunto"]
    assert "Carlos Gómez" in envios[0]["cuerpo"]


async def test_envio_recordatorio_es_idempotente(fabrica: Any, buzon: Any) -> None:
    """P-39: La ejecución reiterada no despacha recordatorios duplicados para el mismo turno."""
    turno, _, pac_usr = await _crear_entorno_turno(fabrica, delta_horas=23.5)

    async with SessionLocal() as db:
        primera = await procesar_recordatorios_24h(db)
        assert primera == 1

        # Segunda corrida inmediata
        segunda = await procesar_recordatorios_24h(db)
        assert segunda == 0

    # Sigue habiendo un único correo
    envios = buzon.de(pac_usr.email)
    assert len(envios) == 1


async def test_turnos_fuera_de_ventana_no_se_notifican(fabrica: Any, buzon: Any) -> None:
    """Turnos a más de 25 horas o pasados no reciben recordatorio."""
    _t_futuro, _, p_futuro = await _crear_entorno_turno(fabrica, delta_horas=72.0)
    _t_pasado, _, p_pasado = await _crear_entorno_turno(fabrica, delta_horas=-1.0)

    async with SessionLocal() as db:
        total = await procesar_recordatorios_24h(db)
        assert total == 0

    assert len(buzon.de(p_futuro.email)) == 0
    assert len(buzon.de(p_pasado.email)) == 0


async def test_turnos_cancelados_no_reciben_recordatorio(fabrica: Any, buzon: Any) -> None:
    """Turnos cancelados dentro de la ventana de 24 horas no deben recibir recordatorio."""
    _t_canc, _, p_canc = await _crear_entorno_turno(
        fabrica, delta_horas=23.8, estado=EstadoTurno.CANCELADO
    )

    async with SessionLocal() as db:
        total = await procesar_recordatorios_24h(db)
        assert total == 0

    assert len(buzon.de(p_canc.email)) == 0
