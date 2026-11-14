"""Flags y paths de las cookies, y contrato de `/auth/me` (C3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings
from app.db.models.usuario import Usuario
from app.db.session import SessionLocal

settings = get_settings()
PASSWORD = "Password123!"


def _crudo(respuesta, nombre: str) -> str:
    cabeceras = respuesta.headers.get_list("set-cookie")
    for cabecera in cabeceras:
        if cabecera.startswith(f"{nombre}="):
            return cabecera
    raise AssertionError(f"no se encontró la cookie {nombre} en {cabeceras!r}")


async def test_flags_de_cookies(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)

    respuesta = await client.post(
        "/api/v1/auth/login", json={"dni": usuario.dni, "password": PASSWORD}
    )
    assert respuesta.status_code == 200

    cookies = respuesta.headers.get_list("set-cookie")
    assert len(cookies) == 2, cookies

    refresh = _crudo(respuesta, "refresh_token")
    assert "HttpOnly" in refresh
    assert "Path=/api/v1/auth" in refresh
    assert "samesite=lax" in refresh.lower()
    assert "Max-Age=604800" in refresh
    assert "Secure" not in refresh  # COOKIE_SECURE=false en desarrollo y tests

    csrf = _crudo(respuesta, "csrf_token")
    assert "HttpOnly" not in csrf, "si fuera httpOnly el SPA no podría leerla"
    assert "Path=/api/v1" in csrf
    assert "Max-Age=604800" in csrf


async def test_me_sin_sesion(client) -> None:
    respuesta = await client.get("/api/v1/auth/me")

    assert respuesta.status_code == 401
    assert respuesta.headers["content-type"] == "application/problem+json"
    assert respuesta.json()["code"] == "NO_AUTENTICADO"
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


async def test_me_solo_con_cookie_no_alcanza(client, sesion, fabrica) -> None:
    """La cookie de refresh no autentica: el acceso va en el header."""
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)

    respuesta = await client.get("/api/v1/auth/me")

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "NO_AUTENTICADO"


async def test_me_con_sesion(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD, telefono="1145678901")
    await sesion.login(usuario.dni, PASSWORD)

    respuesta = await client.get("/api/v1/auth/me", headers=sesion.bearer)

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["id_usuario"] == str(usuario.id_usuario)
    assert datos["dni"] == usuario.dni
    assert datos["email"] == usuario.email
    assert datos["telefono"] == "1145678901"
    assert datos["debe_cambiar_password"] is False
    assert datos["ultimo_login"] is not None


def _token_expirado(id_usuario) -> str:
    ahora = datetime.now(UTC) - timedelta(hours=1)
    return jwt.encode(
        {
            "sub": str(id_usuario),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": ahora,
            "exp": ahora + timedelta(minutes=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


async def test_me_con_token_expirado(client, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)

    respuesta = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {_token_expirado(usuario.id_usuario)}"},
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "TOKEN_INVALIDO"
    assert "invalid_token" in respuesta.headers["WWW-Authenticate"]


async def test_me_con_token_manipulado(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)

    respuesta = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {sesion.access[:-2]}xx"},
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "TOKEN_INVALIDO"


async def test_me_de_cuenta_deshabilitada_tras_el_login(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)

    async with SessionLocal() as session:
        fila = await session.get(Usuario, usuario.id_usuario)
        assert fila is not None
        fila.habilitado = False
        await session.commit()

    respuesta = await client.get("/api/v1/auth/me", headers=sesion.bearer)

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "CUENTA_DESHABILITADA"
