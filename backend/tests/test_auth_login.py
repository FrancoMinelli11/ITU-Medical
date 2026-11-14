"""P-05, P-06, P-07 y C1 (login con costo uniforme)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core import security
from app.db.models.auditoria import Auditoria
from app.db.models.usuario import Usuario
from app.db.session import SessionLocal

PASSWORD = "Password123!"


async def test_login_ok(client, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)

    respuesta = await client.post(
        "/api/v1/auth/login", json={"dni": usuario.dni, "password": PASSWORD}
    )

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["token_type"] == "bearer"
    assert datos["expires_in"] == 900
    assert datos["access_token"]
    assert datos["usuario"]["dni"] == usuario.dni
    assert datos["usuario"]["email"] == usuario.email
    assert datos["usuario"]["rol"] == "PACIENTE"
    assert datos["usuario"]["email_verificado"] is True
    assert datos["debe_cambiar_password"] is False
    assert "password_hash" not in datos["usuario"]

    # El refresh queda en cookie httpOnly y el CSRF en una cookie legible.
    assert client.cookies.get("refresh_token")
    assert client.cookies.get("csrf_token")
    assert "refresh_token" not in datos


async def test_login_actualiza_ultimo_login(client, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)

    await client.post("/api/v1/auth/login", json={"dni": usuario.dni, "password": PASSWORD})

    async with SessionLocal() as session:
        fila = await session.get(Usuario, usuario.id_usuario)
        assert fila is not None
        assert fila.ultimo_login is not None


async def test_password_incorrecta(client, fabrica) -> None:
    """P-06: misma respuesta que un DNI inexistente, sin filtrar la causa."""
    usuario = await fabrica.crear(password=PASSWORD)

    respuesta = await client.post(
        "/api/v1/auth/login", json={"dni": usuario.dni, "password": "OtraPassword1!"}
    )

    assert respuesta.status_code == 401
    assert respuesta.headers["content-type"] == "application/problem+json"
    problema = respuesta.json()
    assert problema["code"] == "CREDENCIALES_INVALIDAS"
    assert "refresh_token" not in {
        cookie.split("=")[0] for cookie in respuesta.headers.get_list("set-cookie")
    }


async def test_login_dni_inexistente(client, fabrica) -> None:
    await fabrica.crear(password=PASSWORD)

    respuesta = await client.post(
        "/api/v1/auth/login", json={"dni": "29999999", "password": PASSWORD}
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "CREDENCIALES_INVALIDAS"


async def test_cuenta_deshabilitada(client, fabrica) -> None:
    """P-07: no puede entrar. Hacia afuera es un 401 igual al resto (C1)."""
    usuario = await fabrica.crear(password=PASSWORD, habilitado=False)

    respuesta = await client.post(
        "/api/v1/auth/login", json={"dni": usuario.dni, "password": PASSWORD}
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "CREDENCIALES_INVALIDAS"

    async with SessionLocal() as session:
        acciones = (
            await session.scalars(select(Auditoria).where(Auditoria.accion == "LOGIN_FALLIDO"))
        ).all()
    assert len(acciones) == 1
    assert acciones[0].datos_despues["motivo"] == "CUENTA_DESHABILITADA"


async def test_login_inexistente_tambien_ejecuta_argon2(client, fabrica, monkeypatch) -> None:
    """C1: el camino "DNI inexistente" verifica contra el hash dummy.

    Se espía `verify_password` en lugar de medir tiempos: un assert de reloj es
    la receta para un test flaky en CI.
    """
    await fabrica.crear(password=PASSWORD)
    hashes: list[str] = []
    original = security.verify_password

    def espia(password: str, password_hash: str) -> bool:
        hashes.append(password_hash)
        return original(password, password_hash)

    monkeypatch.setattr(security, "verify_password", espia)

    respuesta = await client.post(
        "/api/v1/auth/login", json={"dni": "29999999", "password": PASSWORD}
    )

    assert respuesta.status_code == 401
    assert hashes == [security.DUMMY_PASSWORD_HASH]


async def test_login_con_espacios_alrededor_del_dni(client, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)

    respuesta = await client.post(
        "/api/v1/auth/login", json={"dni": f" {usuario.dni} ", "password": PASSWORD}
    )

    assert respuesta.status_code == 200


@pytest.mark.parametrize(
    "dni",
    ["123456", "123456789", "1234abcd", ""],
    ids=["seis_digitos", "nueve_digitos", "con_letras", "vacio"],
)
async def test_dni_invalido_es_400(client, dni: str) -> None:
    respuesta = await client.post("/api/v1/auth/login", json={"dni": dni, "password": PASSWORD})

    assert respuesta.status_code == 400
    problema = respuesta.json()
    assert problema["code"] == "VALIDACION"
    assert problema["errors"][0]["field"] == "body.dni"
