"""Pruebas de agenda médica, horarios, bloqueos y disponibilidad (RF-04, RF-17, RF-26)."""

from __future__ import annotations

from datetime import date, timedelta
from datetime import datetime as dt
from datetime import time as dtime
from typing import Any

from app.core.timezone import LOCAL_TZ, now_utc, to_local
from app.db.models.enums import EstadoTurno, RolUsuario
from app.db.models.paciente import Paciente
from app.db.models.turno import Turno
from app.db.session import SessionLocal

PASSWORD = "Password123!"


async def _admin(fabrica, sesion):
    usuario = await fabrica.crear(
        rol=RolUsuario.ADMINISTRADOR,
        password=PASSWORD,
        nombre="Admin",
        apellido="General",
    )
    await sesion.login(usuario.dni, PASSWORD)
    return usuario


async def _crear_medico(client, sesion, fabrica) -> str:
    res_esp = await client.post(
        "/api/v1/especialidades",
        json={"nombre": f"Esp-{now_utc().timestamp()}"},
        headers=sesion.mutacion(),
    )
    id_esp = res_esp.json()["id_especialidad"]

    alta = await client.post(
        "/api/v1/medicos",
        json={
            "dni": f"{int(now_utc().timestamp()) % 89999999 + 10000000}",
            "email": f"med-{now_utc().timestamp()}@turnos.local",
            "nombre": "Doctor",
            "apellido": "Prueba",
            "id_especialidad": id_esp,
        },
        headers=sesion.mutacion(),
    )
    return alta.json()["id_medico"]


async def test_horarios_superpuestos_rechazados(client, sesion, fabrica) -> None:
    """P-27: comprobar que el sistema rechace horarios médicos superpuestos."""
    await _admin(fabrica, sesion)
    id_medico = await _crear_medico(client, sesion, fabrica)

    # Dos bloques el mismo lunes (dia_semana=0) que se superponen (08:00 a 12:00 y 10:00 a 14:00)
    payload = {
        "horarios": [
            {
                "dia_semana": 0,
                "hora_inicio": "08:00:00",
                "hora_fin": "12:00:00",
                "duracion_minutos": 30,
            },
            {
                "dia_semana": 0,
                "hora_inicio": "10:00:00",
                "hora_fin": "14:00:00",
                "duracion_minutos": 30,
            },
        ]
    }

    respuesta = await client.put(
        f"/api/v1/medicos/{id_medico}/horarios", json=payload, headers=sesion.mutacion()
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "HORARIOS_SUPERPUESTOS"


async def test_configurar_horarios_ok(client, sesion, fabrica) -> None:
    await _admin(fabrica, sesion)
    id_medico = await _crear_medico(client, sesion, fabrica)

    payload = {
        "horarios": [
            {
                "dia_semana": 0,
                "hora_inicio": "08:00:00",
                "hora_fin": "12:00:00",
                "duracion_minutos": 30,
            },
            {
                "dia_semana": 2,
                "hora_inicio": "14:00:00",
                "hora_fin": "18:00:00",
                "duracion_minutos": 30,
            },
        ]
    }

    respuesta = await client.put(
        f"/api/v1/medicos/{id_medico}/horarios", json=payload, headers=sesion.mutacion()
    )

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert len(datos) == 2
    assert datos[0]["dia_semana"] == 0
    assert datos[1]["dia_semana"] == 2


async def test_cambio_horarios_afecta_turnos_rechazado(client, sesion, fabrica) -> None:
    """P-28: el cambio de horario que afecte turnos ya reservados es rechazado."""
    admin = await _admin(fabrica, sesion)
    id_medico = await _crear_medico(client, sesion, fabrica)

    # Horario inicial: Miércoles (dia 2) de 08:00 a 12:00
    await client.put(
        f"/api/v1/medicos/{id_medico}/horarios",
        json={
            "horarios": [
                {
                    "dia_semana": 2,
                    "hora_inicio": "08:00:00",
                    "hora_fin": "12:00:00",
                    "duracion_minutos": 30,
                }
            ]
        },
        headers=sesion.mutacion(),
    )

    # Crear un turno un próximo miércoles a las 09:00
    paciente_user = await fabrica.crear(rol=RolUsuario.PACIENTE)
    ahora_local = to_local(now_utc())
    # Buscar el próximo miércoles
    dias_hasta_miercoles = (2 - ahora_local.weekday() + 7) % 7
    if dias_hasta_miercoles == 0:
        dias_hasta_miercoles = 7
    proximo_miercoles = ahora_local.date() + timedelta(days=dias_hasta_miercoles)

    turno_inicio_local = dt.combine(proximo_miercoles, dtime(9, 0), tzinfo=LOCAL_TZ)
    turno_inicio_utc = turno_inicio_local.astimezone()

    async with SessionLocal() as db:
        paciente = await db.scalar(
            Paciente.__table__.select().where(Paciente.id_usuario == paciente_user.id_usuario)
        )
        assert paciente is not None
        turno = Turno(
            id_paciente=paciente.id_paciente,
            id_medico=id_medico,
            fecha_hora=turno_inicio_utc,
            duracion_minutos=30,
            estado=EstadoTurno.RESERVADO,
            id_usuario_creador=admin.id_usuario,
        )
        db.add(turno)
        await db.commit()

    # Intentar cambiar el horario de los miércoles a solo la tarde (14:00 a 18:00)
    res_cambio = await client.put(
        f"/api/v1/medicos/{id_medico}/horarios",
        json={
            "horarios": [
                {
                    "dia_semana": 2,
                    "hora_inicio": "14:00:00",
                    "hora_fin": "18:00:00",
                    "duracion_minutos": 30,
                }
            ]
        },
        headers=sesion.mutacion(),
    )

    assert res_cambio.status_code == 409
    assert res_cambio.json()["code"] == "TURNOS_AFECTADOS_POR_HORARIO"
    assert len(res_cambio.json()["errors"]) == 1


async def test_bloqueo_con_turnos_rechazado_y_bloqueo_ok(client, sesion, fabrica) -> None:
    """P-40: crear un bloqueo que solapa turnos existentes es rechazado."""
    admin = await _admin(fabrica, sesion)
    id_medico = await _crear_medico(client, sesion, fabrica)

    paciente_user = await fabrica.crear(rol=RolUsuario.PACIENTE)
    turno_hora = now_utc() + timedelta(days=5)

    async with SessionLocal() as db:
        paciente = await db.scalar(
            Paciente.__table__.select().where(Paciente.id_usuario == paciente_user.id_usuario)
        )
        assert paciente is not None
        turno = Turno(
            id_paciente=paciente.id_paciente,
            id_medico=id_medico,
            fecha_hora=turno_hora,
            duracion_minutos=30,
            estado=EstadoTurno.RESERVADO,
            id_usuario_creador=admin.id_usuario,
        )
        db.add(turno)
        await db.commit()

    # Intentar crear un bloqueo que abarca ese turno -> debe dar 409
    payload_solapado: dict[str, Any] = {
        "inicio": (turno_hora - timedelta(hours=1)).isoformat(),
        "fin": (turno_hora + timedelta(hours=1)).isoformat(),
        "motivo": "Congreso médico",
    }
    res_bloqueo = await client.post(
        f"/api/v1/medicos/{id_medico}/bloqueos",
        json=payload_solapado,
        headers=sesion.mutacion(),
    )
    assert res_bloqueo.status_code == 409
    assert res_bloqueo.json()["code"] == "TURNOS_AFECTADOS_POR_BLOQUEO"

    # Crear bloqueo en un horario libre -> debe dar 201
    payload_libre: dict[str, Any] = {
        "inicio": (turno_hora + timedelta(days=2)).isoformat(),
        "fin": (turno_hora + timedelta(days=2, hours=3)).isoformat(),
        "motivo": "Licencia",
    }
    res_ok = await client.post(
        f"/api/v1/medicos/{id_medico}/bloqueos",
        json=payload_libre,
        headers=sesion.mutacion(),
    )
    assert res_ok.status_code == 201
    id_bloqueo = res_ok.json()["id_bloqueo"]

    # Eliminar bloqueo
    res_del = await client.delete(
        f"/api/v1/medicos/{id_medico}/bloqueos/{id_bloqueo}",
        headers=sesion.mutacion(),
    )
    assert res_del.status_code == 204


async def test_consultar_disponibilidad_y_agenda(client, sesion, fabrica) -> None:
    """RF-04: consultar disponibilidad excluyendo turnos ocupados y bloqueos."""
    await _admin(fabrica, sesion)
    id_medico = await _crear_medico(client, sesion, fabrica)

    # Configurar horario todos los días de 08:00 a 10:00 con turnos de 30 min (4 slots diarios)
    horarios = [
        {
            "dia_semana": dia,
            "hora_inicio": "08:00:00",
            "hora_fin": "10:00:00",
            "duracion_minutos": 30,
        }
        for dia in range(7)
    ]
    await client.put(
        f"/api/v1/medicos/{id_medico}/horarios",
        json={"horarios": horarios},
        headers=sesion.mutacion(),
    )

    manana = date.today() + timedelta(days=1)
    pasado = date.today() + timedelta(days=2)

    # Consultar disponibilidad
    res_disp = await client.get(
        f"/api/v1/medicos/{id_medico}/disponibilidad",
        params={"fecha_desde": manana.isoformat(), "fecha_hasta": pasado.isoformat()},
        headers=sesion.bearer,
    )
    assert res_disp.status_code == 200
    slots = res_disp.json()["slots"]
    # 2 días * 4 slots = 8 slots disponibles
    assert len(slots) == 8

    # Consultar agenda
    res_agenda = await client.get(
        f"/api/v1/medicos/{id_medico}/agenda",
        params={"fecha_desde": manana.isoformat(), "fecha_hasta": pasado.isoformat()},
        headers=sesion.bearer,
    )
    assert res_agenda.status_code == 200
    assert "turnos" in res_agenda.json()
    assert "bloqueos" in res_agenda.json()
