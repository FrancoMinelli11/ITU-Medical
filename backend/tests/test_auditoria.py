"""P-30: toda operación de identidad deja rastro en `AUDITORIA`."""

from __future__ import annotations

from sqlalchemy import select

from app.db.models.auditoria import Auditoria
from app.db.session import SessionLocal

PASSWORD = "Password123!"


async def _auditorias() -> list[Auditoria]:
    async with SessionLocal() as session:
        return list((await session.scalars(select(Auditoria).order_by(Auditoria.fecha_hora))).all())


async def test_login_exitoso(client, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)

    respuesta = await client.post(
        "/api/v1/auth/login",
        json={"dni": usuario.dni, "password": PASSWORD},
        headers={"X-Request-ID": "prueba-auditoria-1"},
    )
    assert respuesta.status_code == 200

    filas = await _auditorias()
    assert len(filas) == 1
    fila = filas[0]
    assert fila.accion == "LOGIN_EXITOSO"
    assert fila.entidad == "usuario"
    assert fila.id_usuario == usuario.id_usuario
    assert fila.entidad_id == usuario.id_usuario
    assert str(fila.ip) == "127.0.0.1"
    assert fila.request_id == "prueba-auditoria-1"
    assert fila.datos_despues == {"rol": "PACIENTE", "dni": usuario.dni}


async def test_login_fallido_con_dni_conocido(client, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)

    await client.post("/api/v1/auth/login", json={"dni": usuario.dni, "password": "Otra12345!"})

    filas = await _auditorias()
    assert [fila.accion for fila in filas] == ["LOGIN_FALLIDO"]
    assert filas[0].id_usuario == usuario.id_usuario
    assert filas[0].datos_despues["motivo"] == "PASSWORD_INCORRECTA"


async def test_login_fallido_con_dni_inexistente(client) -> None:
    await client.post("/api/v1/auth/login", json={"dni": "29999999", "password": PASSWORD})

    filas = await _auditorias()
    assert [fila.accion for fila in filas] == ["LOGIN_FALLIDO"]
    assert filas[0].id_usuario is None
    assert filas[0].entidad_id is None
    assert filas[0].datos_despues["motivo"] == "USUARIO_INEXISTENTE"


async def test_refresh_y_logout_dejan_rastro(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)
    await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": sesion.csrf})
    await client.post("/api/v1/auth/logout", headers=sesion.mutacion())

    acciones = [fila.accion for fila in await _auditorias()]
    assert acciones == ["LOGIN_EXITOSO", "REFRESH", "LOGOUT"]
