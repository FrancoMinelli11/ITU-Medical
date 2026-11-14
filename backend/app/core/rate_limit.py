"""Rate limiting de RN-37 sobre Redis.

No se usa el decorador de `slowapi`: su `key_func` es síncrona y no puede leer
el body (el DNI y el email viven ahí), y RN-37 cuenta **intentos fallidos**, no
requests. Se comparte el mismo storage (`RATE_LIMIT_STORAGE_URL`) con dos
contadores de ventana fija: uno por clave de negocio y otro por IP.

Ventana fija desde el primer intento: `INCR` + `EXPIRE` en un único script Lua
para que el TTL no se resetee en cada intento (lo que haría el bloqueo infinito).
"""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any, cast

from limits import parse
from redis.asyncio import Redis

from app.core.exceptions import ApiError

if TYPE_CHECKING:
    from limits import RateLimitItem

_SCRIPT_REGISTRAR = """
local cantidad = redis.call('INCR', KEYS[1])
if cantidad == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return cantidad
"""


class RateLimiter:
    def __init__(self, redis: Redis, *, prefijo: str, limite: str) -> None:
        self._redis = redis
        self._prefijo = prefijo
        self._item: RateLimitItem = parse(limite)
        self._ttl = max(1, int(self._item.get_expiry()))

    @property
    def maximo(self) -> int:
        return self._item.amount

    def clave(self, valor: str) -> str:
        return f"rate:{self._prefijo}:{valor}"

    async def bloqueo_restante(self, valor: str) -> int | None:
        """Segundos de bloqueo si ya se alcanzó el límite, o `None`."""
        clave = self.clave(valor)
        crudo = await self._redis.get(clave)
        if crudo is None:
            return None
        if int(crudo) < self._item.amount:
            return None
        ttl = await self._redis.ttl(clave)
        return ttl if isinstance(ttl, int) and ttl > 0 else self._ttl

    async def registrar(self, valor: str) -> int:
        cantidad = await cast(
            Awaitable[Any],
            self._redis.eval(_SCRIPT_REGISTRAR, 1, self.clave(valor), str(self._ttl)),
        )
        return int(cantidad)

    async def reiniciar(self, valor: str) -> None:
        await self._redis.delete(self.clave(valor))


async def verificar_limites(*pares: tuple[RateLimiter, str]) -> None:
    """Lanza 429 con `Retry-After` si alguna clave está bloqueada.

    Se evalúa antes de verificar la contraseña (P-36): el 6.º intento no vuelve
    a costar argon2id.
    """
    for limiter, valor in pares:
        espera = await limiter.bloqueo_restante(valor)
        if espera is not None:
            raise ApiError(
                429,
                "RATE_LIMIT_EXCEDIDO",
                "Demasiados intentos",
                "Superaste el límite de intentos. Esperá unos minutos y volvé a probar.",
                headers={"Retry-After": str(espera)},
            )
