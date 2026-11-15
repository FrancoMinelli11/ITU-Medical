"""Pruebas de cancelación habitual, solicitudes rápidas y resolución (RF-08, RF-09, RF-10, RF-24).

Cubre:
- P-12: Cancelación habitual (al menos 24 hs de anticipación)
- P-13: Cancelación rápida (menos de 24 hs)
- P-14: Solicitud con motivo obligatorio
- P-15: Resolución de solicitud por recepción (aprobación y rechazo)
- P-16: Cancelación desde recepción
"""

from __future__ import annotations

from datetime import datetime as dt
from datetime import time as dtime
from datetime import timedelta
from typing import Any

from sqlalchemy import select

from app.core.timezone import LOCAL_TZ, now_utc, to_local
from app.db.models.enums import EstadoTurno, RolUsuario
from app.db.models.paciente import Paciente
from app.db.models.turno import Turno
from app.db.session import SessionLocal

PASSWORD = "Password123!"


async def _admin_user(fabrica: Any, sesion: Any) -> Any:
    usuario = await fabrica.crear(
        rol=RolUsuario.ADMINISTRADOR,
        password=PASSWORD,
        nombre="Admin",
        apellido="General",
    )
    await sesion.login(usuario.dni, PASSWORD)
    return usuario


async def _crear_staff(
    fabrica: Any, sesion: Any, rol: RolUsuario = RolUsuario.RECEPCIONISTA
) -> Any:
    usuario = await fabrica.crear(
        rol=rol,
        password=PASSWORD,
        nombre="Recepcionista",
        apellido="Clinica",
    )
    await sesion.login(usuario.dni, PASSWORD)
    return usuario


async def _crear_medico_con_agenda(client: Any, sesion_admin: Any) -> str:
    res_esp = await client.post(
        "/api/v1/especialidades",
        json={"nombre": f"Esp-{int(now_utc().timestamp() * 1000)}"},
        headers=sesion_admin.mutacion(),
    )
    id_esp = res_esp.json()["id_especialidad"]

    alta = await client.post(
        "/api/v1/medicos",
        json={
            "dni": f"3{int(now_utc().timestamp() * 1000) % 8999999 + 1000000}",
            "email": f"med-{int(now_utc().timestamp() * 1000)}@example.com",
            "nombre": "Doctor",
            "apellido": "Pediatra",
            "id_especialidad": id_esp,
        },
        headers=sesion_admin.mutacion(),
    )
    assert alta.status_code == 201, alta.text
    id_medico = str(alta.json()["id_medico"])

    # Horario todos los días de 08:00 a 18:00
    horarios = [
        {
            "dia_semana": dia,
            "hora_inicio": "08:00:00",
            "hora_fin": "18:00:00",
            "duracion_minutos": 30,
        }
        for dia in range(7)
    ]
    await client.put(
        f"/api/v1/medicos/{id_medico}/horarios",
        json={"horarios": horarios},
        headers=sesion_admin.mutacion(),
    )
    return id_medico


def _calcular_slot(dias: int, hora: int = 10, minuto: int = 0) -> dt:
    fecha_base = (to_local(now_utc()) + timedelta(days=dias)).date()
    local_slot = dt.combine(fecha_base, dtime(hora, minuto), tzinfo=LOCAL_TZ)
    return local_slot.astimezone()


async def test_cancelacion_habitual_mas_de_24hs_y_libera_horario(
    client: Any, sesion: Any, fabrica: Any, buzon: Any
) -> None:
    """P-12, RF-08: cancelación habitual exitosa (>= 24 horas) y liberación de slot."""
    await _admin_user(fabrica, sesion)
    id_medico = await _crear_medico_con_agenda(client, sesion)

    paciente = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    await sesion.login(paciente.dni, PASSWORD)

    # Reservar un turno para dentro de 3 días (faltan > 24 hs)
    slot = _calcular_slot(dias=3, hora=10, minuto=0)
    res_reserva = await client.post(
        "/api/v1/turnos",
        json={"id_medico": id_medico, "fecha_hora": slot.isoformat()},
        headers=sesion.mutacion(),
    )
    assert res_reserva.status_code == 201
    id_turno = res_reserva.json()["id_turno"]

    # Cancelar el turno como paciente
    res_cancel = await client.post(
        f"/api/v1/turnos/{id_turno}/cancelar",
        json={"motivo": "Viaje imprevisto"},
        headers=sesion.mutacion(),
    )
    assert res_cancel.status_code == 200
    datos = res_cancel.json()
    assert datos["estado"] == "CANCELADO"
    assert datos["motivo_cancelacion"] == "HABITUAL"

    # Notificación enviada
    envios = buzon.de(paciente.email)
    cancel_mails = [e for e in envios if "Cancelación de turno" in e["asunto"]]
    assert len(cancel_mails) == 1

    # Verificar que el horario quedó liberado: otro paciente puede reservarlo
    otro_paciente = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    await sesion.login(otro_paciente.dni, PASSWORD)
    res_re_reserva = await client.post(
        "/api/v1/turnos",
        json={"id_medico": id_medico, "fecha_hora": slot.isoformat()},
        headers=sesion.mutacion(),
    )
    assert res_re_reserva.status_code == 201


async def test_cancelacion_menos_de_24hs_rechaza_habitual_y_permite_rapida(
    client: Any, sesion: Any, fabrica: Any
) -> None:
    """P-13, RF-09: cuando faltan menos de 24 horas, la habitual da 400 y se habilita la rápida."""
    admin = await _admin_user(fabrica, sesion)
    id_medico = await _crear_medico_con_agenda(client, sesion)

    paciente = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )

    # Crear turno directo en BD dentro de 4 horas (menos de 24 hs)
    slot_proximo = now_utc() + timedelta(hours=4)
    async with SessionLocal() as db:
        id_paciente = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == paciente.id_usuario)
        )
        assert id_paciente is not None
        turno = Turno(
            id_paciente=id_paciente,
            id_medico=id_medico,
            fecha_hora=slot_proximo,
            duracion_minutos=30,
            estado=EstadoTurno.RESERVADO,
            id_usuario_creador=admin.id_usuario,
        )
        db.add(turno)
        await db.commit()
        id_turno = str(turno.id_turno)

    await sesion.login(paciente.dni, PASSWORD)

    # 1. Intentar cancelación habitual -> 400 PLAZO_CANCELACION_EXCEDIDO
    res_hab = await client.post(
        f"/api/v1/turnos/{id_turno}/cancelar",
        json={"motivo": "No llego"},
        headers=sesion.mutacion(),
    )
    assert res_hab.status_code == 400
    assert res_hab.json()["code"] == "PLAZO_CANCELACION_EXCEDIDO"

    # 2. Solicitar cancelación rápida -> 201 Created
    res_rap = await client.post(
        f"/api/v1/turnos/{id_turno}/solicitar-cancelacion",
        json={"motivo": "Urgencia familiar de último momento"},
        headers=sesion.mutacion(),
    )
    assert res_rap.status_code == 201
    datos_solicitud = res_rap.json()
    assert datos_solicitud["estado"] == "PENDIENTE"
    assert datos_solicitud["motivo"] == "Urgencia familiar de último momento"


async def test_solicitud_cancelacion_rapida_valida_motivo(
    client: Any, sesion: Any, fabrica: Any
) -> None:
    """P-14, RF-09: la solicitud requiere explicación obligatoria del motivo."""
    admin = await _admin_user(fabrica, sesion)
    id_medico = await _crear_medico_con_agenda(client, sesion)

    paciente = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    slot_proximo = now_utc() + timedelta(hours=5)

    async with SessionLocal() as db:
        id_paciente = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == paciente.id_usuario)
        )
        assert id_paciente is not None
        turno = Turno(
            id_paciente=id_paciente,
            id_medico=id_medico,
            fecha_hora=slot_proximo,
            duracion_minutos=30,
            estado=EstadoTurno.RESERVADO,
            id_usuario_creador=admin.id_usuario,
        )
        db.add(turno)
        await db.commit()
        id_turno = str(turno.id_turno)

    await sesion.login(paciente.dni, PASSWORD)

    # Motivo demasiado corto (< 5 caracteres) -> 400
    res_invalido = await client.post(
        f"/api/v1/turnos/{id_turno}/solicitar-cancelacion",
        json={"motivo": "no"},
        headers=sesion.mutacion(),
    )
    assert res_invalido.status_code == 400


async def test_resolucion_solicitud_cancelacion_por_recepcion(
    client: Any, sesion: Any, fabrica: Any, buzon: Any
) -> None:
    """P-15, RF-09: recepción puede aprobar o rechazar la solicitud de cancelación rápida."""
    admin = await _admin_user(fabrica, sesion)
    id_medico = await _crear_medico_con_agenda(client, sesion)

    paciente = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    slot_proximo = now_utc() + timedelta(hours=6)

    async with SessionLocal() as db:
        id_paciente = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == paciente.id_usuario)
        )
        assert id_paciente is not None
        turno = Turno(
            id_paciente=id_paciente,
            id_medico=id_medico,
            fecha_hora=slot_proximo,
            duracion_minutos=30,
            estado=EstadoTurno.RESERVADO,
            id_usuario_creador=admin.id_usuario,
        )
        db.add(turno)
        await db.commit()
        id_turno = str(turno.id_turno)

    # 1. Paciente crea la solicitud rápida
    await sesion.login(paciente.dni, PASSWORD)
    res_sol = await client.post(
        f"/api/v1/turnos/{id_turno}/solicitar-cancelacion",
        json={"motivo": "Accidente vial en camino al consultorio"},
        headers=sesion.mutacion(),
    )
    assert res_sol.status_code == 201
    id_solicitud = res_sol.json()["id_solicitud"]

    # 2. Recepcionista lista las solicitudes pendientes
    await _crear_staff(fabrica, sesion, RolUsuario.RECEPCIONISTA)
    res_lista = await client.get(
        "/api/v1/solicitudes-cancelacion",
        params={"estado": "PENDIENTE"},
        headers=sesion.bearer,
    )
    assert res_lista.status_code == 200
    ids_pendientes = [s["id_solicitud"] for s in res_lista.json()]
    assert id_solicitud in ids_pendientes

    # 3. Recepcionista aprueba la solicitud
    res_res = await client.post(
        f"/api/v1/solicitudes-cancelacion/{id_solicitud}/resolver",
        json={"aprobada": True, "detalle": "Motivo justificado"},
        headers=sesion.mutacion(),
    )
    assert res_res.status_code == 200
    assert res_res.json()["estado"] == "APROBADA"

    # Verificar que el turno pasó a CANCELADO en la BD
    async with SessionLocal() as db:
        t = await db.get(Turno, id_turno)
        assert t is not None
        assert t.estado == "CANCELADO"
        assert t.motivo_cancelacion == "RAPIDA"

    # Correo al paciente recibido
    envios = buzon.de(paciente.email)
    assert any("Cancelación de turno" in e["asunto"] for e in envios)


async def test_cancelacion_desde_recepcion_con_motivo_y_trazabilidad(
    client: Any, sesion: Any, fabrica: Any, buzon: Any
) -> None:
    """P-16, RF-10, RF-24: recepción puede cancelar cualquier turno con motivo y trazabilidad."""
    await _admin_user(fabrica, sesion)
    id_medico = await _crear_medico_con_agenda(client, sesion)

    recepcionista = await _crear_staff(fabrica, sesion, RolUsuario.RECEPCIONISTA)

    paciente = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    slot = _calcular_slot(dias=2, hora=11, minuto=0)

    # Recepción crea el turno
    res_turno = await client.post(
        "/api/v1/turnos/recepcion",
        json={
            "dni_paciente": paciente.dni,
            "id_medico": id_medico,
            "fecha_hora": slot.isoformat(),
        },
        headers=sesion.mutacion(),
    )
    assert res_turno.status_code == 201
    id_turno = res_turno.json()["id_turno"]

    # Recepción cancela el turno con motivo BLOQUEO_AGENDA
    res_cancel = await client.post(
        f"/api/v1/turnos/{id_turno}/cancelar-recepcion",
        json={"motivo": "BLOQUEO_AGENDA", "detalle": "Médico con licencia médica urgente"},
        headers=sesion.mutacion(),
    )
    assert res_cancel.status_code == 200
    datos = res_cancel.json()
    assert datos["estado"] == "CANCELADO"
    assert datos["motivo_cancelacion"] == "BLOQUEO_AGENDA"

    # Verificar datos en la BD
    async with SessionLocal() as db:
        t = await db.get(Turno, id_turno)
        assert t is not None
        assert t.estado == "CANCELADO"
        assert t.id_usuario_cancelacion == recepcionista.id_usuario
        assert t.fecha_hora_cancelacion is not None
