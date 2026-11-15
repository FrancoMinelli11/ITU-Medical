"""RF-21, RN-31, RN-32, RN-37, CU-12, P-34, P-35 y C2: recuperación de contraseña."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select, update

from app.core.security import sha256_hex
from app.core.timezone import now_utc
from app.db.models.auditoria import Auditoria
from app.db.models.enums import EstadoNotificacion, TipoNotificacion
from app.db.models.notificacion import Notificacion
from app.db.models.recuperacion_password import RecuperacionPassword
from app.db.models.usuario import Usuario
from app.db.session import SessionLocal

PASSWORD = "Password123!"
NUEVA = "NuevaClave456!"
GENERICO = (
    "Si los datos coinciden con una cuenta, te enviamos un correo para restablecer la contraseña."
)


async def _solicitar(client, email: str, dni: str):
    return await client.post("/api/v1/auth/recuperar-password", json={"email": email, "dni": dni})


async def _restablecer(client, token: str, password: str):
    return await client.post(
        "/api/v1/auth/restablecer-password",
        json={"token": token, "password": password},
    )


async def _crear_usuario(fabrica, **kwargs) -> Usuario:
    return await fabrica.crear(password=PASSWORD, **kwargs)


async def test_solicitud_con_par_valido(client, fabrica, buzon) -> None:
    usuario = await _crear_usuario(
        fabrica, email="recupera@example.com", dni="30555666", nombre="Rita"
    )

    respuesta = await _solicitar(client, usuario.email, usuario.dni)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"mensaje": GENERICO}
    assert len(buzon.de(usuario.email, buzon.ASUNTO_RECUPERACION)) == 1

    async with SessionLocal() as session:
        fila = await session.scalar(
            select(RecuperacionPassword).where(
                RecuperacionPassword.id_usuario == usuario.id_usuario
            )
        )
        assert fila is not None
        assert fila.usado is False
        assert fila.fecha_expiracion - now_utc() > timedelta(minutes=50)

        notificacion = await session.scalar(
            select(Notificacion).where(Notificacion.id_usuario_destinatario == usuario.id_usuario)
        )
        assert notificacion is not None
        assert notificacion.tipo == TipoNotificacion.RECUPERACION_PASSWORD
        assert notificacion.estado == EstadoNotificacion.PENDIENTE

        acciones = (await session.scalars(select(Auditoria))).all()
        assert "RECUPERACION_SOLICITADA" in {fila.accion for fila in acciones}


async def test_par_inexistente_respuesta_generica(client, fabrica, buzon) -> None:
    """P-34: misma respuesta, sin correo y sin fila de token."""
    usuario = await _crear_usuario(fabrica, email="otro@example.com")

    respuesta = await _solicitar(client, usuario.email, "39999999")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"mensaje": GENERICO}
    assert buzon.envios == []
    async with SessionLocal() as session:
        filas = (await session.scalars(select(RecuperacionPassword))).all()
        assert filas == []


async def test_correo_inexistente_respuesta_generica(client, buzon) -> None:
    respuesta = await _solicitar(client, "nadie@example.com", "30555666")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"mensaje": GENERICO}
    assert buzon.envios == []


async def test_usuario_deshabilitado_no_recibe_correo(client, fabrica, buzon) -> None:
    usuario = await _crear_usuario(fabrica, email="inactivo@example.com", habilitado=False)

    respuesta = await _solicitar(client, usuario.email, usuario.dni)

    assert respuesta.status_code == 200
    assert buzon.envios == []


async def test_restablecer_ok(client, fabrica, buzon) -> None:
    usuario = await _crear_usuario(fabrica, email="restablece@example.com")
    await _solicitar(client, usuario.email, usuario.dni)
    token = buzon.token(usuario.email, buzon.ASUNTO_RECUPERACION)

    respuesta = await _restablecer(client, token, NUEVA)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["mensaje"].startswith("Contraseña actualizada")

    viejo = await client.post("/api/v1/auth/login", json={"dni": usuario.dni, "password": PASSWORD})
    assert viejo.status_code == 401

    nuevo = await client.post("/api/v1/auth/login", json={"dni": usuario.dni, "password": NUEVA})
    assert nuevo.status_code == 200
    assert nuevo.json()["debe_cambiar_password"] is False

    async with SessionLocal() as session:
        fila = await session.scalar(
            select(RecuperacionPassword).where(RecuperacionPassword.token_hash == sha256_hex(token))
        )
        assert fila is not None
        assert fila.usado is True
        acciones = [fila.accion for fila in (await session.scalars(select(Auditoria))).all()]
        assert "RECUPERACION_CONSUMIDA" in acciones


async def test_token_expirado(client, fabrica, buzon) -> None:
    """P-35: 400 y la contraseña no cambia."""
    usuario = await _crear_usuario(fabrica, email="expira@example.com")
    await _solicitar(client, usuario.email, usuario.dni)
    token = buzon.token(usuario.email, buzon.ASUNTO_RECUPERACION)

    async with SessionLocal() as session:
        await session.execute(
            update(RecuperacionPassword)
            .where(RecuperacionPassword.token_hash == sha256_hex(token))
            .values(fecha_expiracion=now_utc() - timedelta(minutes=1))
        )
        await session.commit()

    respuesta = await _restablecer(client, token, NUEVA)

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "TOKEN_EXPIRADO"
    sigue = await client.post("/api/v1/auth/login", json={"dni": usuario.dni, "password": PASSWORD})
    assert sigue.status_code == 200


async def test_token_usado(client, fabrica, buzon) -> None:
    usuario = await _crear_usuario(fabrica, email="usado@example.com")
    await _solicitar(client, usuario.email, usuario.dni)
    token = buzon.token(usuario.email, buzon.ASUNTO_RECUPERACION)
    assert (await _restablecer(client, token, NUEVA)).status_code == 200

    respuesta = await _restablecer(client, token, "OtraClave789!")

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "TOKEN_USADO"


async def test_token_inexistente(client) -> None:
    respuesta = await _restablecer(client, "token-que-no-existe-1234567890", NUEVA)

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "TOKEN_INVALIDO"


async def test_password_nueva_debil_es_400(client, fabrica, buzon) -> None:
    """RN-28 en el restablecimiento, con el formato de error habitual."""
    usuario = await _crear_usuario(fabrica, email="debil@example.com")
    await _solicitar(client, usuario.email, usuario.dni)
    token = buzon.token(usuario.email, buzon.ASUNTO_RECUPERACION)

    respuesta = await _restablecer(client, token, "corta")

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "VALIDACION"
    assert respuesta.json()["errors"][0]["field"] == "body.password"


async def test_password_igual_a_la_anterior(client, fabrica, buzon) -> None:
    usuario = await _crear_usuario(fabrica, email="igual@example.com")
    await _solicitar(client, usuario.email, usuario.dni)
    token = buzon.token(usuario.email, buzon.ASUNTO_RECUPERACION)

    respuesta = await _restablecer(client, token, PASSWORD)

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "PASSWORD_SIN_CAMBIOS"


async def test_reenvio_invalida_el_token_anterior(client, fabrica, buzon) -> None:
    """RN-32: cada solicitud invalida la anterior."""
    usuario = await _crear_usuario(fabrica, email="renueva@example.com")
    await _solicitar(client, usuario.email, usuario.dni)
    primero = buzon.token(usuario.email, buzon.ASUNTO_RECUPERACION)

    await _solicitar(client, usuario.email, usuario.dni)
    segundo = buzon.token(usuario.email, buzon.ASUNTO_RECUPERACION)
    assert primero != segundo

    viejo = await _restablecer(client, primero, NUEVA)
    assert viejo.status_code == 400
    assert viejo.json()["code"] == "TOKEN_USADO"

    nuevo = await _restablecer(client, segundo, NUEVA)
    assert nuevo.status_code == 200


async def test_solicitud_tiene_rate_limit(client) -> None:
    """RN-37: 3 solicitudes por correo en 1 hora."""
    for intento in range(3):
        respuesta = await _solicitar(client, "limite@example.com", "30555666")
        assert respuesta.status_code == 200, f"intento {intento + 1}"

    bloqueado = await _solicitar(client, "limite@example.com", "30555666")

    assert bloqueado.status_code == 429
    assert bloqueado.json()["code"] == "RATE_LIMIT_EXCEDIDO"
    assert int(bloqueado.headers["Retry-After"]) > 0


async def test_restablecer_revoca_las_sesiones(client, sesion, fabrica, buzon) -> None:
    """C2: el restablecimiento cierra todas las familias de refresh abiertas."""
    usuario = await _crear_usuario(fabrica, email="cierra@example.com")
    await sesion.login(usuario.dni, PASSWORD)
    await _solicitar(client, usuario.email, usuario.dni)
    token = buzon.token(usuario.email, buzon.ASUNTO_RECUPERACION)

    assert (await _restablecer(client, token, NUEVA)).status_code == 200

    renovacion = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": sesion.csrf})

    assert renovacion.status_code == 401
    assert renovacion.json()["code"] == "SESION_INVALIDA"
