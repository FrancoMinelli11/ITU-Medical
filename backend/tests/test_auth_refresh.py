"""Rotación de refresh y revocación de familia (S-10)."""

from __future__ import annotations

from sqlalchemy import select

from app.db.models.auditoria import Auditoria
from app.db.models.usuario import Usuario
from app.db.session import SessionLocal

PASSWORD = "Password123!"


def _borra_cookie(respuesta, nombre: str) -> bool:
    """`Max-Age=0` en la cabecera de borrado de `nombre`."""
    return any(
        cabecera.startswith(f"{nombre}=") and "Max-Age=0" in cabecera
        for cabecera in respuesta.headers.get_list("set-cookie")
    )


async def test_rotacion_emite_un_par_nuevo(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)
    refresh_viejo = client.cookies.get("refresh_token")
    csrf_viejo = sesion.csrf

    respuesta = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf_viejo})

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["expires_in"] == 900
    assert datos["usuario"]["dni"] == usuario.dni

    refresh_nuevo = client.cookies.get("refresh_token")
    assert refresh_nuevo and refresh_nuevo != refresh_viejo
    assert sesion.csrf != csrf_viejo

    # El access recién emitido sirve.
    perfil = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {datos['access_token']}"}
    )
    assert perfil.status_code == 200


async def test_reuso_de_refresh_revoca_la_familia(client, sesion, fabrica, nuevo_client) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)
    token_a = client.cookies.get("refresh_token") or ""
    csrf_a = sesion.csrf

    primero = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf_a})
    assert primero.status_code == 200
    token_b = client.cookies.get("refresh_token") or ""
    assert token_b and token_b != token_a

    # Alguien replaya el refresh ya rotado: se asume robo.
    ladron = nuevo_client()
    ladron.cookies.set("refresh_token", token_a, path="/api/v1/auth")
    ladron.cookies.set("csrf_token", csrf_a, path="/api/v1")
    reuso = await ladron.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf_a})

    assert reuso.status_code == 401
    assert reuso.json()["code"] == "SESION_INVALIDA"
    # La respuesta ordena limpiar la cookie del cliente que lo intentó.
    # Se mira la cabecera y no el jar: httpx no borra una cookie cargada a mano
    # (queda con dominio vacío) al recibir el `Set-Cookie` de borrado.
    assert _borra_cookie(reuso, "refresh_token")

    # El hijo legítimo también queda revocado: la familia entera cae.
    csrf_b = client.cookies.get("csrf_token") or ""
    segundo = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf_b})
    assert segundo.status_code == 401
    assert segundo.json()["code"] == "SESION_INVALIDA"

    async with SessionLocal() as session:
        acciones = (
            await session.scalars(
                select(Auditoria).where(Auditoria.accion == "REFRESH_REUTILIZADO")
            )
        ).all()
    assert len(acciones) == 1
    assert acciones[0].id_usuario == usuario.id_usuario


async def test_refresh_sin_cookie(client) -> None:
    respuesta = await client.post("/api/v1/auth/refresh")

    assert respuesta.status_code == 403  # CSRF se evalúa antes que la sesión
    assert respuesta.json()["code"] == "CSRF_INVALIDO"


async def test_refresh_sin_cookie_pero_con_csrf(client) -> None:
    await client.get("/api/v1/auth/csrf")
    csrf = client.cookies.get("csrf_token") or ""

    respuesta = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf})

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "NO_AUTENTICADO"
    limpiadas = [
        cabecera
        for cabecera in respuesta.headers.get_list("set-cookie")
        if cabecera.startswith("refresh_token=")
    ]
    assert limpiadas and "Max-Age=0" in limpiadas[0]


async def test_refresh_token_desconocido(client, sesion, fabrica, nuevo_client) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)
    csrf = sesion.csrf

    falso = nuevo_client()
    falso.cookies.set("refresh_token", "token-que-nunca-existio", path="/api/v1/auth")
    falso.cookies.set("csrf_token", csrf, path="/api/v1")

    respuesta = await falso.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf})

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "SESION_INVALIDA"


async def test_refresh_de_cuenta_deshabilitada(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)
    csrf = sesion.csrf

    async with SessionLocal() as session:
        fila = await session.get(Usuario, usuario.id_usuario)
        assert fila is not None
        fila.habilitado = False
        await session.commit()

    respuesta = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf})

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "SESION_INVALIDA"
    assert client.cookies.get("refresh_token") is None
