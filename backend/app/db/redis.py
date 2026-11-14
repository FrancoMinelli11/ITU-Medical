"""Clientes Redis por request.

Se crea y cierra un cliente por request en lugar de compartir uno global: el
cliente de `redis.asyncio` queda atado al event loop en el que se usa, y los
tests corren cada uno en su propio loop. Sin esto aparecerían errores
"attached to a different loop" al azar con `pytest-asyncio`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()


def _cliente(url: str) -> Redis:
    return cast("Redis", Redis.from_url(url, decode_responses=True))


async def get_rate_limit_redis() -> AsyncIterator[Redis]:
    client = _cliente(settings.rate_limit_storage_url)
    try:
        yield client
    finally:
        await client.aclose()


async def get_refresh_redis() -> AsyncIterator[Redis]:
    client = _cliente(settings.refresh_redis_url)
    try:
        yield client
    finally:
        await client.aclose()
