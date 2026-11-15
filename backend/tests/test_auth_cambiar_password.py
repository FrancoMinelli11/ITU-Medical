"""RF-23, RN-28, RN-29, CU-13, P-33 y C2: cambio de contraseña autenticado."""

from __future__ import annotations

from sqlalchemy import select

from app.db.models.auditoria import Auditoria
from app.db.models.enums import RolUsuario
from app.db.models.usuario import Usuario
from app.db.session import SessionLocal

PASSWORD = "Password123!"
NUEVA = "NuevaClave456!"


async def _cambiar(client, sesion, actual: str, nueva: str):
    return await client.post(
        "/api/v1/auth/cambiar-password",
        json={"password_actual": actual, "password_nueva": nueva},
        headers=sesion.mutacion(),
    )


async def test_cambiar_password_ok(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)

    respuesta = await _cambiar(client, sesion, PASSWORD, NUEVA)

    assert respuesta.status_code == 204, respuesta.text

    viejo = await client.post("/api/v1/auth/login", json={"dni": usuario.dni, "password": PASSWORD})
    assert viejo.status_code == 401
    nuevo = await client.post("/api/v1/auth/login", json={"dni": usuario.dni, "password": NUEVA})
    assert nuevo.status_code == 200

    async with SessionLocal() as session:
        acciones = [fila.accion for fila in (await session.scalars(select(Auditoria))).all()]
        assert "PASSWORD_CAMBIADA" in acciones


async def test_cambiar_password_actual_incorrecta(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)

    respuesta = await _cambiar(client, sesion, "OtraPassword1!", NUEVA)

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "PASSWORD_ACTUAL_INCORRECTA"


async def test_cambiar_password_igual(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)

    respuesta = await _cambiar(client, sesion, PASSWORD, PASSWORD)

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "PASSWORD_SIN_CAMBIOS"


async def test_cambiar_password_debil(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)

    respuesta = await _cambiar(client, sesion, PASSWORD, "corta")

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "VALIDACION"
    assert respuesta.json()["errors"][0]["field"] == "body.password_nueva"


async def test_cambiar_password_exige_csrf(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)

    respuesta = await client.post(
        "/api/v1/auth/cambiar-password",
        json={"password_actual": PASSWORD, "password_nueva": NUEVA},
        headers=sesion.bearer,
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "CSRF_INVALIDO"


async def test_cambiar_password_sin_sesion(client) -> None:
    """El CSRF corre antes que la autenticación: se bootstrapea para llegar al 401."""
    await client.get("/api/v1/auth/csrf")

    respuesta = await client.post(
        "/api/v1/auth/cambiar-password",
        json={"password_actual": PASSWORD, "password_nueva": NUEVA},
        headers={"X-CSRF-Token": client.cookies.get("csrf_token") or ""},
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "NO_AUTENTICADO"


async def test_cambiar_password_revoca_las_sesiones(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)

    assert (await _cambiar(client, sesion, PASSWORD, NUEVA)).status_code == 204

    renovacion = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": sesion.csrf})

    assert renovacion.status_code == 401
    assert renovacion.json()["code"] == "SESION_INVALIDA"


async def test_primer_ingreso_ok(client, sesion, fabrica) -> None:
    """P-33 / CU-13: la cuenta de recepción cambia el DNI por una clave real."""
    usuario = await fabrica.crear(
        rol=RolUsuario.RECEPCIONISTA,
        password=None,
        debe_cambiar_password=True,
    )
    datos = await sesion.login(usuario.dni, usuario.dni)
    assert datos["debe_cambiar_password"] is True

    respuesta = await client.post(
        "/api/v1/auth/primer-ingreso",
        json={"password_nueva": NUEVA},
        headers=sesion.mutacion(),
    )

    assert respuesta.status_code == 204, respuesta.text

    acceso = await client.get("/api/v1/auth/me", headers=sesion.bearer)
    assert acceso.json()["debe_cambiar_password"] is False

    async with SessionLocal() as session:
        fila = await session.get(Usuario, usuario.id_usuario)
        assert fila is not None
        assert fila.debe_cambiar_password is False
        acciones = [fila.accion for fila in (await session.scalars(select(Auditoria))).all()]
        assert "PRIMER_INGRESO_COMPLETADO" in acciones

    # Ahora sí puede operar: el rol de recepción ya no está bloqueado por C3.
    listado = await client.get(
        "/api/v1/pacientes", headers={"Authorization": f"Bearer {datos['access_token']}"}
    )
    assert listado.status_code == 200

    nuevo_login = await client.post(
        "/api/v1/auth/login", json={"dni": usuario.dni, "password": NUEVA}
    )
    assert nuevo_login.status_code == 200
    assert nuevo_login.json()["debe_cambiar_password"] is False


async def test_primer_ingreso_ya_realizado(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)

    respuesta = await client.post(
        "/api/v1/auth/primer-ingreso",
        json={"password_nueva": NUEVA},
        headers=sesion.mutacion(),
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "PRIMER_INGRESO_YA_REALIZADO"


async def test_primer_ingreso_igual_a_la_temporal(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=None, debe_cambiar_password=True)
    await sesion.login(usuario.dni, usuario.dni)

    respuesta = await client.post(
        "/api/v1/auth/primer-ingreso",
        json={"password_nueva": usuario.dni},
        headers=sesion.mutacion(),
    )

    assert respuesta.status_code == 400
    # El DNI no cumple RN-28, así que la validación del schema gana primero.
    assert respuesta.json()["code"] in {"VALIDACION", "PASSWORD_SIN_CAMBIOS"}


async def test_primer_ingreso_exige_csrf(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=None, debe_cambiar_password=True)
    await sesion.login(usuario.dni, usuario.dni)

    respuesta = await client.post(
        "/api/v1/auth/primer-ingreso",
        json={"password_nueva": NUEVA},
        headers=sesion.bearer,
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "CSRF_INVALIDO"
