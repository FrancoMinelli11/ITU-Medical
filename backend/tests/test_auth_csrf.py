"""CSRF double-submit: exenciones, header faltante y header que no coincide."""

from __future__ import annotations

PASSWORD = "Password123!"


async def test_login_esta_exento(client, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)

    respuesta = await client.post(
        "/api/v1/auth/login", json={"dni": usuario.dni, "password": PASSWORD}
    )

    assert respuesta.status_code == 200


async def test_logout_sin_header_da_403(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)
    assert sesion.csrf

    respuesta = await client.post("/api/v1/auth/logout")

    assert respuesta.status_code == 403
    assert respuesta.headers["content-type"] == "application/problem+json"
    assert respuesta.json()["code"] == "CSRF_INVALIDO"
    assert respuesta.headers["Cache-Control"] == "no-store"

    # No se revocó nada: el refresh sigue funcionando.
    renovado = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": sesion.csrf})
    assert renovado.status_code == 200


async def test_logout_con_header_incorrecto_da_403(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)

    respuesta = await client.post(
        "/api/v1/auth/logout", headers={**sesion.bearer, "X-CSRF-Token": "no-es-el-token"}
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "CSRF_INVALIDO"

    renovado = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": sesion.csrf})
    assert renovado.status_code == 200


async def test_logout_con_header_correcto(client, sesion, fabrica, nuevo_client) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)
    refresh_viejo = client.cookies.get("refresh_token") or ""
    csrf_viejo = sesion.csrf

    respuesta = await client.post("/api/v1/auth/logout", headers=sesion.mutacion())

    assert respuesta.status_code == 204
    assert client.cookies.get("refresh_token") is None
    assert client.cookies.get("csrf_token") is None

    # Un cliente que replaya el refresh revocado ya no puede renovar.
    otro = nuevo_client()
    # Sin `domain=`: `http.cookiejar` descarta dominios de una sola etiqueta
    # ("localhost") y la cookie nunca se enviaría.
    otro.cookies.set("refresh_token", refresh_viejo, path="/api/v1/auth")
    otro.cookies.set("csrf_token", csrf_viejo, path="/api/v1")
    renovado = await otro.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf_viejo})
    assert renovado.status_code == 401
    assert renovado.json()["code"] == "SESION_INVALIDA"


async def test_refresh_no_esta_exento(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)

    respuesta = await client.post("/api/v1/auth/refresh")

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "CSRF_INVALIDO"


async def test_refresh_sin_cookie_csrf_da_403(client, sesion, fabrica) -> None:
    """Si el SPA perdió la cookie CSRF, debe pedir una nueva con GET /auth/csrf."""
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)
    token = sesion.csrf

    client.cookies.delete("csrf_token")
    respuesta = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": token})

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "CSRF_INVALIDO"


async def test_bootstrap_de_csrf(client) -> None:
    respuesta = await client.get("/api/v1/auth/csrf")

    assert respuesta.status_code == 204
    crudo = respuesta.headers["set-cookie"]
    assert crudo.startswith("csrf_token=")
    assert "HttpOnly" not in crudo
    assert "Path=/;" in crudo
    assert client.cookies.get("csrf_token")


async def test_get_no_exige_csrf(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)

    respuesta = await client.get("/api/v1/auth/me", headers=sesion.bearer)

    assert respuesta.status_code == 200
