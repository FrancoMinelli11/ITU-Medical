"""RF-01, RN-28, RN-31, P-01, P-02, P-03 y P-31: alta web de paciente."""

from __future__ import annotations

import pytest
from redis.asyncio import Redis
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import sha256_hex
from app.db.models.auditoria import Auditoria
from app.db.models.enums import EstadoNotificacion, TipoNotificacion
from app.db.models.notificacion import Notificacion
from app.db.models.paciente import Paciente
from app.db.models.usuario import Usuario
from app.db.models.verificacion_email import VerificacionEmail
from app.db.session import SessionLocal

PASSWORD = "Password123!"
REGISTRO = {
    "dni": "30111222",
    "email": "ana.gomez@example.com",
    "password": PASSWORD,
    "nombre": "Ana",
    "apellido": "Gómez",
    "telefono": "1145550000",
    "fecha_nacimiento": "1990-05-04",
}


async def _usuario_por_dni(dni: str) -> Usuario | None:
    async with SessionLocal() as session:
        return await session.scalar(select(Usuario).where(Usuario.dni == dni))


async def test_registro_crea_cuenta_y_paciente(client, buzon) -> None:
    respuesta = await client.post("/api/v1/auth/registro", json=REGISTRO)

    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert datos["dni"] == REGISTRO["dni"]
    assert datos["email"] == REGISTRO["email"]
    assert datos["email_verificado"] is False
    assert datos["debe_cambiar_password"] is False
    assert datos["habilitado"] is True
    assert datos["telefono"] == REGISTRO["telefono"]
    assert datos["fecha_nacimiento"] == REGISTRO["fecha_nacimiento"]

    usuario = await _usuario_por_dni(REGISTRO["dni"])
    assert usuario is not None
    assert usuario.rol == "PACIENTE"
    assert usuario.email_verificado is False
    assert usuario.password_hash != PASSWORD

    async with SessionLocal() as session:
        paciente = await session.scalar(
            select(Paciente).where(Paciente.id_usuario == usuario.id_usuario)
        )
        assert paciente is not None
        assert str(paciente.telefono) == REGISTRO["telefono"]

        notificacion = await session.scalar(
            select(Notificacion).where(Notificacion.id_usuario_destinatario == usuario.id_usuario)
        )
        assert notificacion is not None
        assert notificacion.tipo == TipoNotificacion.VERIFICACION_EMAIL
        assert notificacion.estado == EstadoNotificacion.PENDIENTE

        verificacion = await session.scalar(
            select(VerificacionEmail).where(VerificacionEmail.id_usuario == usuario.id_usuario)
        )
        assert verificacion is not None
        assert verificacion.usado is False
        token_hash = verificacion.token_hash

        auditorias = (
            await session.scalars(
                select(Auditoria).where(Auditoria.id_usuario == usuario.id_usuario)
            )
        ).all()
        assert "ALTA_PACIENTE_WEB" in {fila.accion for fila in auditorias}

    # El token plano solo vive en el correo; en la base queda el hash (RN-31).
    token = buzon.token(REGISTRO["email"])
    assert token_hash == sha256_hex(token)
    assert token not in token_hash


async def test_registro_no_verificado_puede_iniciar_sesion(client, buzon) -> None:
    await client.post("/api/v1/auth/registro", json=REGISTRO)

    respuesta = await client.post(
        "/api/v1/auth/login",
        json={"dni": REGISTRO["dni"], "password": PASSWORD},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["usuario"]["email_verificado"] is False


async def test_registro_dni_duplicado(client, fabrica) -> None:
    existente = await fabrica.crear(dni="30111222")

    respuesta = await client.post("/api/v1/auth/registro", json=REGISTRO)

    assert respuesta.status_code == 409
    assert respuesta.headers["content-type"] == "application/problem+json"
    assert respuesta.json()["code"] == "DNI_DUPLICADO"
    assert existente.dni == REGISTRO["dni"]


async def test_registro_email_duplicado(client, fabrica) -> None:
    await fabrica.crear(email=REGISTRO["email"])

    respuesta = await client.post("/api/v1/auth/registro", json=REGISTRO)

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "EMAIL_DUPLICADO"


async def test_registro_normaliza_el_correo(client, buzon) -> None:
    respuesta = await client.post(
        "/api/v1/auth/registro",
        json={**REGISTRO, "email": "Ana.Gomez@Example.COM"},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["email"] == "ana.gomez@example.com"


@pytest.mark.parametrize(
    ("password", "motivo"),
    [
        ("Abc123", "corta"),
        ("SoloLetras!", "sin_numero"),
        ("1234567890", "sin_letra"),
        ("A" * 128 + "1", "demasiado_larga"),
    ],
    ids=["corta", "sin_numero", "sin_letra", "demasiado_larga"],
)
async def test_registro_password_debil_es_400(client, password: str, motivo: str) -> None:
    """P-31 / RN-28: se valida en el schema y sale como cualquier otro 400."""
    respuesta = await client.post("/api/v1/auth/registro", json={**REGISTRO, "password": password})

    assert respuesta.status_code == 400, motivo
    problema = respuesta.json()
    assert problema["code"] == "VALIDACION"
    assert problema["errors"][0]["field"] == "body.password"


@pytest.mark.parametrize(
    "dni",
    ["123456", "123456789", "1234abcd"],
    ids=["seis_digitos", "nueve_digitos", "con_letras"],
)
async def test_registro_dni_invalido_es_400(client, dni: str) -> None:
    respuesta = await client.post("/api/v1/auth/registro", json={**REGISTRO, "dni": dni})

    assert respuesta.status_code == 400
    assert respuesta.json()["errors"][0]["field"] == "body.dni"


async def test_registro_nombre_vacio_es_400(client) -> None:
    respuesta = await client.post("/api/v1/auth/registro", json={**REGISTRO, "nombre": "   "})

    assert respuesta.status_code == 400
    campos = {error["field"] for error in respuesta.json()["errors"]}
    assert "body.nombre" in campos


async def test_registro_no_permite_campos_extra(client) -> None:
    respuesta = await client.post(
        "/api/v1/auth/registro", json={**REGISTRO, "rol": "ADMINISTRADOR"}
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "VALIDACION"


async def test_registro_encola_el_correo_en_arq(client) -> None:
    """RNF-11: la notificación se encola después del commit de la transacción."""
    respuesta = await client.post("/api/v1/auth/registro", json=REGISTRO)
    assert respuesta.status_code == 201

    redis = Redis.from_url(get_settings().arq_redis_url)
    try:
        encontrados = []
        async for clave in redis.scan_iter(match="*"):
            # La cola de ARQ es un sorted set (`arq:queue`): `GET` daría WRONGTYPE.
            if await redis.type(clave) != b"string":
                continue
            valor = await redis.get(clave)
            if valor and b"enviar_email" in valor:
                encontrados.append(clave)
        assert encontrados, "no hay ningún job `enviar_email` encolado en ARQ"
        assert await redis.zcard("arq:queue") >= 1
    finally:
        await redis.aclose()
