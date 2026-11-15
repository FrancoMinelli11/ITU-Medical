"""Pruebas de llegadas, sala de espera y ausencias (RF-11, RF-12, RF-15).

Cubre:
- P-17: Registro de llegada (RESERVADO -> EN_ESPERA)
- P-18: Llegada duplicada (rechazada con 409)
- P-19: Orden de atención según RF-12 (puntuales ordenados por horario de turno)
- P-20: Tolerancia (llegada > 10 min tarde pierde prioridad)
- P-21: Ausencias individuales y cierre de jornada
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
        apellido="Hospital",
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
            "apellido": "Oftalmo",
            "id_especialidad": id_esp,
        },
        headers=sesion_admin.mutacion(),
    )
    assert alta.status_code == 201, alta.text
    id_medico = str(alta.json()["id_medico"])

    # Agenda: 08:00 a 18:00 todos los días
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


async def test_registro_llegada_ok_y_duplicada_rechazada(
    client: Any, sesion: Any, fabrica: Any
) -> None:
    """P-17, P-18, RF-11: registro de llegada exitoso y prevención de llegada duplicada."""
    await _admin_user(fabrica, sesion)
    id_medico = await _crear_medico_con_agenda(client, sesion)
    await _crear_staff(fabrica, sesion, RolUsuario.RECEPCIONISTA)

    paciente = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    fecha_base = (to_local(now_utc()) + timedelta(days=2)).date()
    slot = dt.combine(fecha_base, dtime(10, 0), tzinfo=LOCAL_TZ).astimezone()

    # Crear turno
    res_t = await client.post(
        "/api/v1/turnos/recepcion",
        json={
            "dni_paciente": paciente.dni,
            "id_medico": id_medico,
            "fecha_hora": slot.isoformat(),
        },
        headers=sesion.mutacion(),
    )
    assert res_t.status_code == 201
    id_turno = res_t.json()["id_turno"]

    # 1. Registrar llegada (P-17)
    res_llegada = await client.post(
        f"/api/v1/recepcion/turnos/{id_turno}/llegada",
        headers=sesion.mutacion(),
    )
    assert res_llegada.status_code == 200
    datos = res_llegada.json()
    assert datos["estado"] == "EN_ESPERA"
    assert datos["fecha_hora_llegada"] is not None

    # 2. Intentar registrar llegada duplicada (P-18) -> 409 LLEGADA_YA_REGISTRADA
    res_dup = await client.post(
        f"/api/v1/recepcion/turnos/{id_turno}/llegada",
        headers=sesion.mutacion(),
    )
    assert res_dup.status_code == 409
    assert res_dup.json()["code"] == "LLEGADA_YA_REGISTRADA"


async def test_orden_atencion_y_tolerancia_10_minutos(
    client: Any, sesion: Any, fabrica: Any
) -> None:
    """P-19, P-20, RF-12: orden de atención según puntualidad y tolerancia."""
    admin = await _admin_user(fabrica, sesion)
    id_medico = await _crear_medico_con_agenda(client, sesion)

    # Crear 3 pacientes
    p_puntual_1 = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, nombre="Ana", apellido="Puntual1"
    )
    p_puntual_2 = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, nombre="Bernardo", apellido="Puntual2"
    )
    p_retrasado = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, nombre="Carlos", apellido="Retrasado"
    )

    hoy = to_local(now_utc()).date()
    # Turno 1: Ana a las 10:00 (llega 09:55 -> dentro de tolerancia)
    t1_programado = dt.combine(hoy, dtime(10, 0), tzinfo=LOCAL_TZ).astimezone()
    t1_llegada = dt.combine(hoy, dtime(9, 55), tzinfo=LOCAL_TZ).astimezone()

    # Turno 2: Bernardo a las 10:30 (llega a las 09:30 -> antes que todos, pero su turno es después)
    t2_programado = dt.combine(hoy, dtime(10, 30), tzinfo=LOCAL_TZ).astimezone()
    t2_llegada = dt.combine(hoy, dtime(9, 30), tzinfo=LOCAL_TZ).astimezone()

    # Turno 3: Carlos a las 09:00 (llega a las 09:20 -> 20 min tarde, SUPERÓ tolerancia de 10 min)
    t3_programado = dt.combine(hoy, dtime(9, 0), tzinfo=LOCAL_TZ).astimezone()
    t3_llegada = dt.combine(hoy, dtime(9, 20), tzinfo=LOCAL_TZ).astimezone()

    async with SessionLocal() as db:
        id_p1 = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == p_puntual_1.id_usuario)
        )
        id_p2 = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == p_puntual_2.id_usuario)
        )
        id_p3 = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == p_retrasado.id_usuario)
        )
        assert id_p1 and id_p2 and id_p3

        turno1 = Turno(
            id_paciente=id_p1,
            id_medico=id_medico,
            fecha_hora=t1_programado,
            duracion_minutos=30,
            estado=EstadoTurno.EN_ESPERA,
            fecha_hora_llegada=t1_llegada,
            id_usuario_creador=admin.id_usuario,
        )
        turno2 = Turno(
            id_paciente=id_p2,
            id_medico=id_medico,
            fecha_hora=t2_programado,
            duracion_minutos=30,
            estado=EstadoTurno.EN_ESPERA,
            fecha_hora_llegada=t2_llegada,
            id_usuario_creador=admin.id_usuario,
        )
        turno3 = Turno(
            id_paciente=id_p3,
            id_medico=id_medico,
            fecha_hora=t3_programado,
            duracion_minutos=30,
            estado=EstadoTurno.EN_ESPERA,
            fecha_hora_llegada=t3_llegada,
            id_usuario_creador=admin.id_usuario,
        )
        db.add_all([turno1, turno2, turno3])
        await db.commit()

    # Recepcionista consulta la sala de espera
    await _crear_staff(fabrica, sesion, RolUsuario.RECEPCIONISTA)
    res_sala = await client.get(
        "/api/v1/recepcion/sala-espera",
        params={"id_medico": id_medico, "fecha": hoy.isoformat()},
        headers=sesion.bearer,
    )
    assert res_sala.status_code == 200
    sala = res_sala.json()
    assert len(sala) == 3

    # Orden esperado según RF-12:
    # 1. Ana (Puntual 10:00) -> Primero en el grupo puntual
    # 2. Bernardo (Puntual 10:30) -> Segundo (llegar 09:30 no adelanta a Ana)
    # 3. Carlos (Retrasado 09:00, llegó 09:20) -> Pierde prioridad y pasa al final
    assert sala[0]["paciente_apellido"] == "Puntual1"
    assert sala[0]["orden_atencion"] == 1
    assert sala[0]["en_tolerancia"] is True

    assert sala[1]["paciente_apellido"] == "Puntual2"
    assert sala[1]["orden_atencion"] == 2
    assert sala[1]["en_tolerancia"] is True

    assert sala[2]["paciente_apellido"] == "Retrasado"
    assert sala[2]["orden_atencion"] == 3
    assert sala[2]["en_tolerancia"] is False


async def test_registro_ausencias_individual_y_cierre_jornada(
    client: Any, sesion: Any, fabrica: Any
) -> None:
    """P-21, RF-15: recepción puede marcar ausencias individuales y cierre de jornada."""
    admin = await _admin_user(fabrica, sesion)
    id_medico = await _crear_medico_con_agenda(client, sesion)
    recepcionista = await _crear_staff(fabrica, sesion, RolUsuario.RECEPCIONISTA)

    p1 = await fabrica.crear(rol=RolUsuario.PACIENTE, password=PASSWORD)
    p2 = await fabrica.crear(rol=RolUsuario.PACIENTE, password=PASSWORD)

    hoy = to_local(now_utc()).date()
    slot1 = dt.combine(hoy, dtime(9, 0), tzinfo=LOCAL_TZ).astimezone()
    slot2 = dt.combine(hoy, dtime(9, 30), tzinfo=LOCAL_TZ).astimezone()

    async with SessionLocal() as db:
        id_p1 = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == p1.id_usuario)
        )
        id_p2 = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == p2.id_usuario)
        )
        assert id_p1 and id_p2

        t1 = Turno(
            id_paciente=id_p1,
            id_medico=id_medico,
            fecha_hora=slot1,
            duracion_minutos=30,
            estado=EstadoTurno.RESERVADO,
            id_usuario_creador=admin.id_usuario,
        )
        t2 = Turno(
            id_paciente=id_p2,
            id_medico=id_medico,
            fecha_hora=slot2,
            duracion_minutos=30,
            estado=EstadoTurno.RESERVADO,
            id_usuario_creador=admin.id_usuario,
        )
        db.add_all([t1, t2])
        await db.commit()
        id_t1 = str(t1.id_turno)
        id_t2 = str(t2.id_turno)

    # 1. Marcar ausencia individual de t1
    await sesion.login(recepcionista.dni, PASSWORD)
    res_ind = await client.post(
        f"/api/v1/recepcion/turnos/{id_t1}/ausente",
        headers=sesion.mutacion(),
    )
    assert res_ind.status_code == 200
    assert res_ind.json()["estado"] == "AUSENTE"

    # 2. Cierre de jornada: t2 (que quedó en RESERVADO sin llegada) se marca automáticamente
    res_cierre = await client.post(
        "/api/v1/recepcion/cierre-jornada",
        params={"fecha": hoy.isoformat()},
        headers=sesion.mutacion(),
    )
    assert res_cierre.status_code == 200
    datos_cierre = res_cierre.json()
    assert datos_cierre["total_ausentes"] >= 1
    assert id_t2 in [str(x) for x in datos_cierre["turnos_afectados"]]

    # Verificar que t2 ahora está en AUSENTE
    async with SessionLocal() as db:
        t2_db = await db.get(Turno, id_t2)
        assert t2_db is not None
        assert t2_db.estado == EstadoTurno.AUSENTE
