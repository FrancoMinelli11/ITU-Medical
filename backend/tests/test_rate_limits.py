"""RN-37 / P-36: límites de intentos de login.

El bloqueo se evalúa antes de verificar la contraseña, así que el 6.º intento
devuelve 429 sin gastar argon2id. Los tests no duermen: para simular el fin de
la ventana se borra la clave en Redis.
"""

from __future__ import annotations

from redis.asyncio import Redis
from sqlalchemy import select

from app.core.config import get_settings
from app.core.rate_limit import RateLimiter
from app.db.models.auditoria import Auditoria
from app.db.session import SessionLocal

settings = get_settings()
PASSWORD = "Password123!"
MALA = "MalaPassword1!"


async def _limpiar_clave(valor: str) -> None:
    redis = Redis.from_url(settings.rate_limit_storage_url, decode_responses=True)
    try:
        limiter = RateLimiter(redis, prefijo="login:dni", limite=settings.rate_limit_login_dni)
        await redis.delete(limiter.clave(valor))
    finally:
        await redis.aclose()


async def test_login_dni_bloqueo(client, fabrica) -> None:
    """P-36: intentos 1-5 → 401; el 6.º → 429, no el 5.º."""
    usuario = await fabrica.crear(password=PASSWORD)

    for intento in range(1, 6):
        respuesta = await client.post(
            "/api/v1/auth/login", json={"dni": usuario.dni, "password": MALA}
        )
        assert respuesta.status_code == 401, f"intento {intento}: {respuesta.text}"

    bloqueado = await client.post("/api/v1/auth/login", json={"dni": usuario.dni, "password": MALA})

    assert bloqueado.status_code == 429
    assert bloqueado.headers["content-type"] == "application/problem+json"
    assert bloqueado.json()["code"] == "RATE_LIMIT_EXCEDIDO"
    assert int(bloqueado.headers["Retry-After"]) > 0

    # Ni siquiera con la contraseña correcta se entra durante el bloqueo.
    con_correcta = await client.post(
        "/api/v1/auth/login", json={"dni": usuario.dni, "password": PASSWORD}
    )
    assert con_correcta.status_code == 429

    # El 429 no cuenta como intento nuevo: quedaron 5 fallos auditados.
    async with SessionLocal() as session:
        fallos = (
            await session.scalars(select(Auditoria).where(Auditoria.accion == "LOGIN_FALLIDO"))
        ).all()
    assert len(fallos) == 5


async def test_exito_reinicia_el_contador(client, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)

    for _ in range(4):
        fallo = await client.post("/api/v1/auth/login", json={"dni": usuario.dni, "password": MALA})
        assert fallo.status_code == 401

    assert (
        await client.post("/api/v1/auth/login", json={"dni": usuario.dni, "password": PASSWORD})
    ).status_code == 200

    # Después del éxito el contador arranca de cero: un fallo más no bloquea.
    otro = await client.post("/api/v1/auth/login", json={"dni": usuario.dni, "password": MALA})
    assert otro.status_code == 401


async def test_limite_por_ip(client) -> None:
    """20 fallos desde la misma IP (DNIs distintos) → el 21.º es 429."""
    for indice in range(20):
        respuesta = await client.post(
            "/api/v1/auth/login",
            json={"dni": f"29{indice:06d}", "password": PASSWORD},
        )
        assert respuesta.status_code == 401, f"intento {indice + 1}"

    bloqueado = await client.post(
        "/api/v1/auth/login", json={"dni": "29999999", "password": PASSWORD}
    )

    assert bloqueado.status_code == 429
    assert bloqueado.json()["code"] == "RATE_LIMIT_EXCEDIDO"


async def test_ventana_vencida_permite_entrar(client, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    for _ in range(5):
        await client.post("/api/v1/auth/login", json={"dni": usuario.dni, "password": MALA})
    assert (
        await client.post("/api/v1/auth/login", json={"dni": usuario.dni, "password": PASSWORD})
    ).status_code == 429

    # Equivale a que expire la ventana de 15 minutos.
    await _limpiar_clave(usuario.dni)

    assert (
        await client.post("/api/v1/auth/login", json={"dni": usuario.dni, "password": PASSWORD})
    ).status_code == 200
