"""RF-20, RN-31, RN-32, RN-37, CU-11 y P-41: verificación de correo."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select, update

from app.core.security import sha256_hex
from app.core.timezone import now_utc
from app.db.models.auditoria import Auditoria
from app.db.models.verificacion_email import VerificacionEmail
from app.db.session import SessionLocal

PASSWORD = "Password123!"
REGISTRO = {
    "dni": "30222333",
    "email": "bruno.diaz@example.com",
    "password": PASSWORD,
    "nombre": "Bruno",
    "apellido": "Díaz",
}


async def _registrar(client) -> None:
    respuesta = await client.post("/api/v1/auth/registro", json=REGISTRO)
    assert respuesta.status_code == 201, respuesta.text


async def _verificar(client, token: str):
    return await client.post("/api/v1/auth/verificar-email", json={"token": token})


async def test_token_valido_marca_el_correo(client, buzon) -> None:
    await _registrar(client)
    token = buzon.token(REGISTRO["email"])

    respuesta = await _verificar(client, token)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {
        "email_verificado": True,
        "mensaje": "Correo verificado. Ya podés reservar turnos.",
    }

    async with SessionLocal() as session:
        fila = await session.scalar(
            select(VerificacionEmail).where(VerificacionEmail.token_hash == sha256_hex(token))
        )
        assert fila is not None
        assert fila.usado is True
        acciones = (await session.scalars(select(Auditoria))).all()
        assert {fila.accion for fila in acciones} >= {
            "ALTA_PACIENTE_WEB",
            "VERIFICACION_EMAIL_ENVIADA",
            "EMAIL_VERIFICADO",
        }

    # El login posterior ya reporta el correo verificado.
    datos = await client.post(
        "/api/v1/auth/login", json={"dni": REGISTRO["dni"], "password": PASSWORD}
    )
    assert datos.json()["usuario"]["email_verificado"] is True


async def test_token_inexistente(client) -> None:
    respuesta = await _verificar(client, "token-que-no-existe-1234567890")

    assert respuesta.status_code == 400
    assert respuesta.headers["content-type"] == "application/problem+json"
    assert respuesta.json()["code"] == "TOKEN_INVALIDO"


async def test_token_ya_usado(client, buzon) -> None:
    await _registrar(client)
    token = buzon.token(REGISTRO["email"])
    assert (await _verificar(client, token)).status_code == 200

    respuesta = await _verificar(client, token)

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "TOKEN_USADO"


async def test_token_expirado(client, buzon) -> None:
    await _registrar(client)
    token = buzon.token(REGISTRO["email"])

    async with SessionLocal() as session:
        await session.execute(
            update(VerificacionEmail)
            .where(VerificacionEmail.token_hash == sha256_hex(token))
            .values(fecha_expiracion=now_utc() - timedelta(minutes=1))
        )
        await session.commit()

    respuesta = await _verificar(client, token)

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "TOKEN_EXPIRADO"


async def test_reenvio_invalida_el_token_anterior(client, buzon) -> None:
    """RN-32: solo hay un token vigente a la vez."""
    await _registrar(client)
    primero = buzon.token(REGISTRO["email"])

    reenvio = await client.post(
        "/api/v1/auth/reenviar-verificacion", json={"email": REGISTRO["email"]}
    )
    assert reenvio.status_code == 202
    segundo = buzon.token(REGISTRO["email"])
    assert segundo != primero

    viejo = await _verificar(client, primero)
    assert viejo.status_code == 400
    assert viejo.json()["code"] == "TOKEN_USADO"

    nuevo = await _verificar(client, segundo)
    assert nuevo.status_code == 200


async def test_reenvio_de_correo_inexistente_es_generico(client, buzon) -> None:
    """No se revela si el correo existe (RF-21 / RN-37)."""
    respuesta = await client.post(
        "/api/v1/auth/reenviar-verificacion", json={"email": "nadie@example.com"}
    )

    assert respuesta.status_code == 202
    assert respuesta.json()["mensaje"]
    assert buzon.envios == []


async def test_reenvio_no_hace_nada_si_ya_esta_verificado(client, buzon) -> None:
    await _registrar(client)
    token = buzon.token(REGISTRO["email"])
    assert (await _verificar(client, token)).status_code == 200
    envios_previos = len(buzon.envios)

    respuesta = await client.post(
        "/api/v1/auth/reenviar-verificacion", json={"email": REGISTRO["email"]}
    )

    assert respuesta.status_code == 202
    assert len(buzon.envios) == envios_previos


async def test_reenvio_tiene_rate_limit(client) -> None:
    """RN-37: 3 reenvíos por correo en 1 hora; el 4.º es 429."""
    for intento in range(3):
        respuesta = await client.post(
            "/api/v1/auth/reenviar-verificacion", json={"email": "limite@example.com"}
        )
        assert respuesta.status_code == 202, f"intento {intento + 1}"

    bloqueado = await client.post(
        "/api/v1/auth/reenviar-verificacion", json={"email": "limite@example.com"}
    )

    assert bloqueado.status_code == 429
    assert bloqueado.json()["code"] == "RATE_LIMIT_EXCEDIDO"
    assert int(bloqueado.headers["Retry-After"]) > 0


async def test_token_muy_corto_es_400(client) -> None:
    respuesta = await _verificar(client, "corto")

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "VALIDACION"
    assert respuesta.json()["errors"][0]["field"] == "body.token"
