"""Pruebas de gestión de profesionales médicos (RF-18)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import select

from app.core.timezone import now_utc
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


async def _crear_especialidad(client, sesion, nombre: str = "Clínica") -> str:
    res = await client.post(
        "/api/v1/especialidades", json={"nombre": nombre}, headers=sesion.mutacion()
    )
    return res.json()["id_especialidad"]


async def test_crear_medico_admin(client, sesion, fabrica) -> None:
    await _admin(fabrica, sesion)
    id_esp = await _crear_especialidad(client, sesion, "Cardiología")

    payload: dict[str, Any] = {
        "dni": "35111222",
        "email": "medico.test@example.com",
        "nombre": "Esteban",
        "apellido": "Gómez",
        "id_especialidad": id_esp,
        "matricula": "MN-12345",
    }

    respuesta = await client.post("/api/v1/medicos", json=payload, headers=sesion.mutacion())
    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert datos["dni"] == payload["dni"]
    assert datos["email"] == payload["email"]
    assert datos["matricula"] == "MN-12345"
    assert datos["especialidad_nombre"] == "Cardiología"
    assert datos["activo"] is True


async def test_crear_medico_matricula_duplicada(client, sesion, fabrica) -> None:
    await _admin(fabrica, sesion)
    id_esp = await _crear_especialidad(client, sesion, "Pediatría")

    p1 = {
        "dni": "35111333",
        "email": "medico1@example.com",
        "nombre": "Médico",
        "apellido": "Uno",
        "id_especialidad": id_esp,
        "matricula": "MN-99999",
    }
    r1 = await client.post("/api/v1/medicos", json=p1, headers=sesion.mutacion())
    assert r1.status_code == 201, r1.text

    p2 = {
        "dni": "35111444",
        "email": "medico2@example.com",
        "nombre": "Médico",
        "apellido": "Dos",
        "id_especialidad": id_esp,
        "matricula": "MN-99999",
    }
    r2 = await client.post("/api/v1/medicos", json=p2, headers=sesion.mutacion())
    assert r2.status_code == 409
    assert r2.json()["code"] == "MATRICULA_DUPLICADA"


async def test_listar_y_buscar_medicos(client, sesion, fabrica) -> None:
    await _admin(fabrica, sesion)
    id_esp = await _crear_especialidad(client, sesion, "Traumatología")

    p = {
        "dni": "35888999",
        "email": "traumato@example.com",
        "nombre": "Hernán",
        "apellido": "Crespo",
        "id_especialidad": id_esp,
        "matricula": "MN-77777",
    }
    res_crear = await client.post("/api/v1/medicos", json=p, headers=sesion.mutacion())
    assert res_crear.status_code == 201, res_crear.text

    # Búsqueda por apellido
    res_busqueda = await client.get(
        "/api/v1/medicos", params={"q": "Crespo"}, headers=sesion.bearer
    )
    assert res_busqueda.status_code == 200
    items = res_busqueda.json()["items"]
    assert len(items) == 1
    assert items[0]["apellido"] == "Crespo"

    # Filtrar por especialidad
    res_esp = await client.get(
        "/api/v1/medicos", params={"id_especialidad": id_esp}, headers=sesion.bearer
    )
    assert res_esp.status_code == 200
    assert len(res_esp.json()["items"]) >= 1


async def test_deshabilitar_medico_con_turnos_futuros_falla(client, sesion, fabrica) -> None:
    admin = await _admin(fabrica, sesion)
    id_esp = await _crear_especialidad(client, sesion, "Neurología")

    alta = await client.post(
        "/api/v1/medicos",
        json={
            "dni": "35000999",
            "email": "neuro@example.com",
            "nombre": "Claudio",
            "apellido": "Brito",
            "id_especialidad": id_esp,
        },
        headers=sesion.mutacion(),
    )
    assert alta.status_code == 201, alta.text
    id_medico = alta.json()["id_medico"]

    # Crear un paciente y un turno futuro asignado al médico
    paciente_user = await fabrica.crear(rol=RolUsuario.PACIENTE)

    async with SessionLocal() as db:
        id_paciente = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == paciente_user.id_usuario)
        )
        assert id_paciente is not None
        turno = Turno(
            id_paciente=id_paciente,
            id_medico=id_medico,
            fecha_hora=now_utc() + timedelta(days=2),
            duracion_minutos=30,
            estado=EstadoTurno.RESERVADO,
            id_usuario_creador=admin.id_usuario,
        )
        db.add(turno)
        await db.commit()

    # Intentar desactivar al médico -> debe dar 409 con la lista de turnos (RF-18)
    res_desactivar = await client.patch(
        f"/api/v1/medicos/{id_medico}",
        json={"activo": False},
        headers=sesion.mutacion(),
    )

    assert res_desactivar.status_code == 409
    datos_error = res_desactivar.json()
    assert datos_error["code"] == "MEDICO_CON_TURNOS_FUTUROS"
    assert len(datos_error["errors"]) == 1
    assert datos_error["errors"][0]["duracion_minutos"] == 30
