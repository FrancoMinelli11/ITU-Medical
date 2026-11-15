"""Pruebas de especialidades médicas (RF-18)."""

from __future__ import annotations

from app.db.models.enums import RolUsuario

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


async def _paciente(fabrica, sesion):
    usuario = await fabrica.crear(
        rol=RolUsuario.PACIENTE,
        password=PASSWORD,
    )
    await sesion.login(usuario.dni, PASSWORD)
    return usuario


async def test_crear_especialidad_admin(client, sesion, fabrica) -> None:
    await _admin(fabrica, sesion)

    payload = {"nombre": "Dermatología", "descripcion": "Cuidado de la piel"}
    respuesta = await client.post("/api/v1/especialidades", json=payload, headers=sesion.mutacion())

    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert datos["nombre"] == "Dermatología"
    assert datos["descripcion"] == "Cuidado de la piel"
    assert datos["activa"] is True
    assert "id_especialidad" in datos


async def test_crear_especialidad_sin_permiso(client, sesion, fabrica) -> None:
    await _paciente(fabrica, sesion)

    payload = {"nombre": "Oftalmología"}
    respuesta = await client.post("/api/v1/especialidades", json=payload, headers=sesion.mutacion())

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "SIN_PERMISO"


async def test_crear_especialidad_duplicada(client, sesion, fabrica) -> None:
    await _admin(fabrica, sesion)

    payload = {"nombre": "Cardiología"}
    r1 = await client.post("/api/v1/especialidades", json=payload, headers=sesion.mutacion())
    assert r1.status_code == 201

    # Mismo nombre con diferente capitalización o espacios
    r2 = await client.post(
        "/api/v1/especialidades", json={"nombre": "  cardiología  "}, headers=sesion.mutacion()
    )
    assert r2.status_code == 409
    assert r2.json()["code"] == "ESPECIALIDAD_DUPLICADA"


async def test_listar_especialidades(client, sesion, fabrica) -> None:
    await _admin(fabrica, sesion)

    await client.post(
        "/api/v1/especialidades", json={"nombre": "Pediatría"}, headers=sesion.mutacion()
    )
    r_inactiva = await client.post(
        "/api/v1/especialidades", json={"nombre": "Traumatología"}, headers=sesion.mutacion()
    )
    id_inactiva = r_inactiva.json()["id_especialidad"]

    # Desactivar una
    await client.patch(
        f"/api/v1/especialidades/{id_inactiva}",
        json={"activa": False},
        headers=sesion.mutacion(),
    )

    # Como paciente solo ve activas
    await _paciente(fabrica, sesion)
    res_paciente = await client.get("/api/v1/especialidades", headers=sesion.bearer)
    assert res_paciente.status_code == 200
    nombres = [item["nombre"] for item in res_paciente.json()]
    assert "Pediatría" in nombres
    assert "Traumatología" not in nombres


async def test_actualizar_especialidad(client, sesion, fabrica) -> None:
    await _admin(fabrica, sesion)

    creada = await client.post(
        "/api/v1/especialidades", json={"nombre": "Neurología"}, headers=sesion.mutacion()
    )
    id_esp = creada.json()["id_especialidad"]

    modificada = await client.patch(
        f"/api/v1/especialidades/{id_esp}",
        json={"nombre": "Neurocirugía", "descripcion": "Cirugías complejas"},
        headers=sesion.mutacion(),
    )

    assert modificada.status_code == 200
    datos = modificada.json()
    assert datos["nombre"] == "Neurocirugía"
    assert datos["descripcion"] == "Cirugías complejas"
