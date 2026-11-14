"""P-44 (parcial): expiración de tokens en UTC y TTL exacto del refresh.

El turno de las 23:30 es H4; acá solo se fija que el access vence a los 15
minutos absolutos y que el refresh vive 7 días en Redis.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.security import sha256_hex

settings = get_settings()
PASSWORD = "Password123!"


async def test_expiracion_del_access_token_en_utc(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)

    payload = jwt.decode(
        sesion.access,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"verify_exp": False},
    )

    emitido = datetime.fromtimestamp(payload["iat"], UTC)
    vence = datetime.fromtimestamp(payload["exp"], UTC)
    assert vence - emitido == timedelta(minutes=settings.access_token_expire_minutes)
    assert payload["sub"] == str(usuario.id_usuario)
    assert payload["rol"] == "PACIENTE"
    assert payload["sid"]


async def test_ttl_del_refresh_en_redis(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)
    token = client.cookies.get("refresh_token") or ""

    redis = Redis.from_url(settings.refresh_redis_url, decode_responses=True)
    try:
        ttl = await redis.ttl(f"refresh:tok:{sha256_hex(token)}")
    finally:
        await redis.aclose()

    esperado = settings.refresh_token_expire_days * 24 * 60 * 60
    assert esperado - 10 <= ttl <= esperado


async def test_el_token_plano_no_se_guarda(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    await sesion.login(usuario.dni, PASSWORD)
    token = client.cookies.get("refresh_token") or ""

    redis = Redis.from_url(settings.refresh_redis_url, decode_responses=True)
    try:
        assert await redis.exists(f"refresh:tok:{token}") == 0
        assert await redis.exists(f"refresh:tok:{sha256_hex(token)}") == 1
    finally:
        await redis.aclose()
