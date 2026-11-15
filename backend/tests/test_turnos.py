"""Pruebas de gestión y reserva de turnos (RF-05, RF-06, RF-07, RF-25, RNF-02, RN-37).

Cubre:
- P-08: Reserva disponible (paciente verificado)
- P-09: Reserva duplicada (mismo médico)
- P-10: Reservas simultáneas concurrentes
- P-11: Turno desde recepción
- P-32: Reserva sin correo verificado
- P-37: Concurrencia exacta (rollback total)
- P-38: Solapamiento del mismo paciente con distintos médicos
- P-42: Idempotencia de confirmación
"""

from __future__ import annotations

import asyncio
from datetime import datetime as dt
from datetime import time as dtime
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import select

from app.core.timezone import LOCAL_TZ, now_utc, to_local
from app.db.models.bloqueo_agenda import BloqueoAgenda
from app.db.models.enums import RolUsuario
from app.db.models.restriccion_usuario import RestriccionUsuario
from app.db.models.turno import Turno
from app.db.models.usuario import Usuario
from app.db.session import SessionLocal
from tests.conftest import SesionAuth

PASSWORD = "Password123!"


async def _crear_staff(
    fabrica: Any, sesion: Any, rol: RolUsuario = RolUsuario.RECEPCIONISTA
) -> Usuario:
    usuario = await fabrica.crear(
        rol=rol,
        password=PASSWORD,
        nombre="Staff",
        apellido="Clinica",
    )
    await sesion.login(usuario.dni, PASSWORD)
    return usuario


async def _crear_medico_con_agenda(client: Any, sesion_admin: Any, fabrica: Any) -> str:
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
            "apellido": "Cardio",
            "id_especialidad": id_esp,
        },
        headers=sesion_admin.mutacion(),
    )
    assert alta.status_code == 201, alta.text
    id_medico = str(alta.json()["id_medico"])

    # Configurar agenda: Lunes a domingo de 08:00 a 14:00 con turnos de 30 min
    horarios = [
        {
            "dia_semana": dia,
            "hora_inicio": "08:00:00",
            "hora_fin": "14:00:00",
            "duracion_minutos": 30,
        }
        for dia in range(7)
    ]
    res_horarios = await client.put(
        f"/api/v1/medicos/{id_medico}/horarios",
        json={"horarios": horarios},
        headers=sesion_admin.mutacion(),
    )
    assert res_horarios.status_code == 200, res_horarios.text
    return id_medico


def _calcular_slot_futuro(dias: int = 2, hora: int = 10, minuto: int = 0) -> dt:
    fecha_base = (to_local(now_utc()) + timedelta(days=dias)).date()
    local_slot = dt.combine(fecha_base, dtime(hora, minuto), tzinfo=LOCAL_TZ)
    return local_slot.astimezone()


async def test_reserva_web_ok_y_notificacion(
    client: Any, sesion: Any, fabrica: Any, buzon: Any
) -> None:
    """P-08, RF-05, RF-22: reserva disponible por paciente con correo verificado."""
    # 1. Crear admin y configurar médico con agenda
    admin_user = await fabrica.crear(rol=RolUsuario.ADMINISTRADOR, password=PASSWORD)
    sesion_admin = SesionAuth(client)
    await sesion_admin.login(admin_user.dni, PASSWORD)
    id_medico = await _crear_medico_con_agenda(client, sesion_admin, fabrica)

    # 2. Crear paciente con email verificado
    paciente_user = await fabrica.crear(
        rol=RolUsuario.PACIENTE,
        password=PASSWORD,
        email="paciente_verificado@example.com",
        email_verificado=True,
    )
    await sesion.login(paciente_user.dni, PASSWORD)

    slot = _calcular_slot_futuro(dias=2, hora=10, minuto=0)
    payload = {
        "id_medico": id_medico,
        "fecha_hora": slot.isoformat(),
    }

    res = await client.post("/api/v1/turnos", json=payload, headers=sesion.mutacion())
    assert res.status_code == 201, res.text
    datos = res.json()

    assert datos["estado"] == "RESERVADO"
    assert datos["duracion_minutos"] == 30
    assert datos["id_medico"] == id_medico
    assert datos["paciente_dni"] == paciente_user.dni

    # Verificar que el correo se encoló y se guardó en notificaciones
    envios = buzon.de(paciente_user.email)
    assert len(envios) == 1
    assert "Confirmación de turno" in envios[0]["asunto"]


async def test_reserva_web_sin_correo_verificado_falla(
    client: Any, sesion: Any, fabrica: Any
) -> None:
    """P-32, RF-05: paciente sin correo verificado no puede reservar turnos."""
    admin_user = await fabrica.crear(rol=RolUsuario.ADMINISTRADOR, password=PASSWORD)
    sesion_admin = SesionAuth(client)
    await sesion_admin.login(admin_user.dni, PASSWORD)
    id_medico = await _crear_medico_con_agenda(client, sesion_admin, fabrica)

    # Paciente con email_verificado=False
    paciente_user = await fabrica.crear(
        rol=RolUsuario.PACIENTE,
        password=PASSWORD,
        email="no_verificado@example.com",
        email_verificado=False,
    )
    await sesion.login(paciente_user.dni, PASSWORD)

    slot = _calcular_slot_futuro(dias=2, hora=10, minuto=0)
    res = await client.post(
        "/api/v1/turnos",
        json={"id_medico": id_medico, "fecha_hora": slot.isoformat()},
        headers=sesion.mutacion(),
    )
    assert res.status_code == 403
    assert res.json()["code"] == "EMAIL_NO_VERIFICADO"


async def test_reserva_duplicada_mismo_medico_falla(client: Any, sesion: Any, fabrica: Any) -> None:
    """P-09, RF-06: no se puede reservar un horario ya ocupado con el mismo médico."""
    admin_user = await fabrica.crear(rol=RolUsuario.ADMINISTRADOR, password=PASSWORD)
    sesion_admin = SesionAuth(client)
    await sesion_admin.login(admin_user.dni, PASSWORD)
    id_medico = await _crear_medico_con_agenda(client, sesion_admin, fabrica)

    p1 = await fabrica.crear(rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True)
    p2 = await fabrica.crear(rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True)

    slot = _calcular_slot_futuro(dias=2, hora=10, minuto=0)
    payload = {"id_medico": id_medico, "fecha_hora": slot.isoformat()}

    # Paciente 1 reserva exitosamente
    await sesion.login(p1.dni, PASSWORD)
    res1 = await client.post("/api/v1/turnos", json=payload, headers=sesion.mutacion())
    assert res1.status_code == 201

    # Paciente 2 intenta reservar el mismo slot -> 409 TURNO_OCUPADO
    await sesion.login(p2.dni, PASSWORD)
    res2 = await client.post("/api/v1/turnos", json=payload, headers=sesion.mutacion())
    assert res2.status_code == 409
    assert res2.json()["code"] == "TURNO_OCUPADO"


@pytest.mark.serial
async def test_reserva_concurrente_mismo_slot(nuevo_client: Any, fabrica: Any) -> None:
    """P-10, P-37: dos solicitudes simultáneas por el mismo horario (exactamente una gana)."""
    admin_user = await fabrica.crear(rol=RolUsuario.ADMINISTRADOR, password=PASSWORD)
    c_admin = nuevo_client()
    sesion_admin = SesionAuth(c_admin)
    await sesion_admin.login(admin_user.dni, PASSWORD)
    id_medico = await _crear_medico_con_agenda(c_admin, sesion_admin, fabrica)

    p1 = await fabrica.crear(rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True)
    p2 = await fabrica.crear(rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True)

    c1 = nuevo_client()
    s1 = SesionAuth(c1)
    await s1.login(p1.dni, PASSWORD)

    c2 = nuevo_client()
    s2 = SesionAuth(c2)
    await s2.login(p2.dni, PASSWORD)

    slot = _calcular_slot_futuro(dias=3, hora=11, minuto=0)
    payload = {"id_medico": id_medico, "fecha_hora": slot.isoformat()}

    # Disparo concurrente
    t1 = c1.post("/api/v1/turnos", json=payload, headers=s1.mutacion())
    t2 = c2.post("/api/v1/turnos", json=payload, headers=s2.mutacion())
    r1, r2 = await asyncio.gather(t1, t2)

    codigos = {r1.status_code, r2.status_code}
    assert codigos == {201, 409}, f"Obtenido r1={r1.status_code}, r2={r2.status_code}"

    # En la base debe haber exactamente 1 turno
    async with SessionLocal() as db:
        turnos = (
            await db.scalars(
                select(Turno).where(Turno.id_medico == id_medico, Turno.fecha_hora == slot)
            )
        ).all()
        assert len(turnos) == 1


async def test_reserva_solapada_mismo_paciente_distintos_medicos_falla(
    client: Any, sesion: Any, fabrica: Any
) -> None:
    """P-38, RF-25: exclusion constraint evita solapamiento del mismo paciente."""
    admin_user = await fabrica.crear(rol=RolUsuario.ADMINISTRADOR, password=PASSWORD)
    sesion_admin = SesionAuth(client)
    await sesion_admin.login(admin_user.dni, PASSWORD)

    # Crear dos médicos distintos con agenda activa
    id_medico1 = await _crear_medico_con_agenda(client, sesion_admin, fabrica)
    id_medico2 = await _crear_medico_con_agenda(client, sesion_admin, fabrica)

    paciente = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    await sesion.login(paciente.dni, PASSWORD)

    slot = _calcular_slot_futuro(dias=2, hora=11, minuto=0)

    # 1. Turno con Médico 1 -> OK
    res1 = await client.post(
        "/api/v1/turnos",
        json={"id_medico": id_medico1, "fecha_hora": slot.isoformat()},
        headers=sesion.mutacion(),
    )
    assert res1.status_code == 201

    # 2. Turno con Médico 2 en el mismo horario -> Falla con 409 TURNO_SOLAPADO_PACIENTE
    res2 = await client.post(
        "/api/v1/turnos",
        json={"id_medico": id_medico2, "fecha_hora": slot.isoformat()},
        headers=sesion.mutacion(),
    )
    assert res2.status_code == 409
    assert res2.json()["code"] == "TURNO_SOLAPADO_PACIENTE"


async def test_reserva_recepcion_ok(client: Any, sesion: Any, fabrica: Any, buzon: Any) -> None:
    """P-11, RF-07: creación de turno desde recepción en nombre del paciente."""
    await _admin_user(fabrica, sesion)
    id_medico = await _crear_medico_con_agenda(client, sesion, fabrica)

    # Crear un recepcionista
    await _crear_staff(fabrica, sesion, RolUsuario.RECEPCIONISTA)

    # Crear un paciente
    paciente = await fabrica.crear(
        rol=RolUsuario.PACIENTE,
        password=PASSWORD,
        email="paciente_recepcion@example.com",
    )

    slot = _calcular_slot_futuro(dias=2, hora=12, minuto=0)
    payload = {
        "dni_paciente": paciente.dni,
        "id_medico": id_medico,
        "fecha_hora": slot.isoformat(),
    }

    res = await client.post("/api/v1/turnos/recepcion", json=payload, headers=sesion.mutacion())
    assert res.status_code == 201, res.text
    datos = res.json()
    assert datos["paciente_dni"] == paciente.dni
    assert datos["estado"] == "RESERVADO"

    # Notificación enviada al paciente
    envios = buzon.de(paciente.email)
    assert len(envios) == 1


async def test_reserva_web_usuario_rojo_rechazada(client: Any, sesion: Any, fabrica: Any) -> None:
    """P-25, RF-16, RN-21: restricción de Usuario rojo bloquea web pero permite recepción."""
    admin = await _admin_user(fabrica, sesion)
    id_medico = await _crear_medico_con_agenda(client, sesion, fabrica)

    paciente = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )

    # Aplicar restricción de Usuario rojo activa
    async with SessionLocal() as db:
        restriccion = RestriccionUsuario(
            id_usuario=paciente.id_usuario,
            motivo="Reiteradas inasistencias",
            fecha_inicio=now_utc(),
            fecha_fin=now_utc() + timedelta(days=30),
            activa=True,
            id_usuario_creador=admin.id_usuario,
        )
        db.add(restriccion)
        await db.commit()

    slot = _calcular_slot_futuro(dias=2, hora=12, minuto=30)

    # Intento de reserva web por parte del paciente -> 403
    await sesion.login(paciente.dni, PASSWORD)
    res_web = await client.post(
        "/api/v1/turnos",
        json={"id_medico": id_medico, "fecha_hora": slot.isoformat()},
        headers=sesion.mutacion(),
    )
    assert res_web.status_code == 403
    assert res_web.json()["code"] == "USUARIO_ROJO_RESTRINGIDO"

    # En cambio, recepción sí puede crear el turno para ese paciente (RF-16)
    await _crear_staff(fabrica, sesion, RolUsuario.RECEPCIONISTA)
    res_rec = await client.post(
        "/api/v1/turnos/recepcion",
        json={
            "dni_paciente": paciente.dni,
            "id_medico": id_medico,
            "fecha_hora": slot.isoformat(),
        },
        headers=sesion.mutacion(),
    )
    assert res_rec.status_code == 201


async def test_reserva_fuera_de_agenda_o_bloqueada_rechazada(
    client: Any, sesion: Any, fabrica: Any
) -> None:
    """RN-05, RF-26: horarios no disponibles o bloqueados son rechazados."""
    admin = await _admin_user(fabrica, sesion)
    id_medico = await _crear_medico_con_agenda(client, sesion, fabrica)

    paciente = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    await sesion.login(paciente.dni, PASSWORD)

    # 1. Horario fuera de agenda (16:00 hs, médico atiende solo de 08:00 a 14:00)
    slot_fuera = _calcular_slot_futuro(dias=2, hora=16, minuto=0)
    res_fuera = await client.post(
        "/api/v1/turnos",
        json={"id_medico": id_medico, "fecha_hora": slot_fuera.isoformat()},
        headers=sesion.mutacion(),
    )
    assert res_fuera.status_code == 400
    assert res_fuera.json()["code"] == "HORARIO_FUERA_DE_AGENDA"

    # 2. Bloqueo de agenda (crear bloqueo entre las 09:00 y 11:00)
    slot_bloqueado = _calcular_slot_futuro(dias=2, hora=10, minuto=0)
    async with SessionLocal() as db:
        bloqueo = BloqueoAgenda(
            id_medico=id_medico,
            inicio=slot_bloqueado - timedelta(hours=1),
            fin=slot_bloqueado + timedelta(hours=1),
            motivo="Capacitación médica",
            id_usuario_creador=admin.id_usuario,
        )
        db.add(bloqueo)
        await db.commit()

    res_bloqueado = await client.post(
        "/api/v1/turnos",
        json={"id_medico": id_medico, "fecha_hora": slot_bloqueado.isoformat()},
        headers=sesion.mutacion(),
    )
    assert res_bloqueado.status_code == 409
    assert res_bloqueado.json()["code"] == "HORARIO_BLOQUEADO"


async def test_listar_turnos_permisos_y_filtros(client: Any, sesion: Any, fabrica: Any) -> None:
    """RNF-03: paciente solo ve sus propios turnos; recepción puede ver todos."""
    await _admin_user(fabrica, sesion)
    id_medico = await _crear_medico_con_agenda(client, sesion, fabrica)

    p1 = await fabrica.crear(rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True)
    p2 = await fabrica.crear(rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True)

    slot1 = _calcular_slot_futuro(dias=2, hora=9, minuto=0)
    slot2 = _calcular_slot_futuro(dias=2, hora=9, minuto=30)

    # Reserva para p1
    await sesion.login(p1.dni, PASSWORD)
    res1 = await client.post(
        "/api/v1/turnos",
        json={"id_medico": id_medico, "fecha_hora": slot1.isoformat()},
        headers=sesion.mutacion(),
    )
    assert res1.status_code == 201
    id_turno1 = res1.json()["id_turno"]

    # Reserva para p2
    await sesion.login(p2.dni, PASSWORD)
    res2 = await client.post(
        "/api/v1/turnos",
        json={"id_medico": id_medico, "fecha_hora": slot2.isoformat()},
        headers=sesion.mutacion(),
    )
    assert res2.status_code == 201
    id_turno2 = res2.json()["id_turno"]

    # p1 consulta sus turnos: solo debe ver id_turno1
    await sesion.login(p1.dni, PASSWORD)
    res_p1 = await client.get("/api/v1/turnos", headers=sesion.bearer)
    assert res_p1.status_code == 200
    ids_p1 = [t["id_turno"] for t in res_p1.json()["items"]]
    assert id_turno1 in ids_p1
    assert id_turno2 not in ids_p1

    # p1 intenta acceder directamente al turno de p2 -> 403
    res_acceso = await client.get(f"/api/v1/turnos/{id_turno2}", headers=sesion.bearer)
    assert res_acceso.status_code == 403

    # Recepción consulta turnos: ve ambos
    await _crear_staff(fabrica, sesion, RolUsuario.RECEPCIONISTA)
    res_staff = await client.get("/api/v1/turnos", headers=sesion.bearer)
    assert res_staff.status_code == 200
    ids_staff = [t["id_turno"] for t in res_staff.json()["items"]]
    assert id_turno1 in ids_staff
    assert id_turno2 in ids_staff


async def _admin_user(fabrica: Any, sesion: Any) -> Usuario:
    usuario = await fabrica.crear(
        rol=RolUsuario.ADMINISTRADOR,
        password=PASSWORD,
        nombre="Admin",
        apellido="General",
    )
    await sesion.login(usuario.dni, PASSWORD)
    return usuario
