"""Refresh tokens opacos con rotación y revocación de familia (S-10).

Se guardan en Redis (`REFRESH_REDIS_URL`), nunca en Postgres:

- `refresh:tok:<sha256>` → `{id_usuario, family, usado}`, TTL = 7 días.
- `refresh:family:<uuid>` → `{id_usuario, revocada}`, mismo TTL.
- `refresh:user:<uuid>` → set de familias del usuario, para revocar todo al
  cambiar o restablecer la contraseña (C2).

El token plano solo existe en la cookie. Cuando un token ya consumido vuelve a
aparecer se asume robo y se revoca la familia completa.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast
from uuid import UUID, uuid4

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.security import generate_opaque_token, sha256_hex

settings = get_settings()
TTL = settings.refresh_token_expire_days * 24 * 60 * 60


class EstadoRotacion(StrEnum):
    OK = "OK"
    INVALIDO = "INVALIDO"
    REUSO = "REUSO"
    REVOCADA = "REVOCADA"
    SESION_INEXISTENTE = "SESION_INEXISTENTE"


@dataclass(frozen=True)
class Rotacion:
    estado: EstadoRotacion
    refresh_token: str | None = None
    id_usuario: UUID | None = None
    family_id: str | None = None


# Un único EVAL evita que dos refresh simultáneos del mismo token emitan dos
# hijos válidos: el segundo ve `usado = 1` y dispara la revocación de familia.
_SCRIPT_ROTAR = """
local actual = redis.call('GET', KEYS[1])
if not actual then
  return {'INVALIDO'}
end
local datos = cjson.decode(actual)
if datos.usado == '1' then
  local familia = redis.call('GET', KEYS[3])
  if familia then
    local f = cjson.decode(familia)
    f.revocada = '1'
    redis.call('SET', KEYS[3], cjson.encode(f), 'EX', ARGV[2])
  end
  return {'REUSO', datos.id_usuario, datos.family}
end
local familia = redis.call('GET', KEYS[3])
if not familia then
  return {'SESION_INEXISTENTE', datos.id_usuario, datos.family}
end
local f = cjson.decode(familia)
if f.revocada == '1' then
  return {'REVOCADA', datos.id_usuario, datos.family}
end
datos.usado = '1'
redis.call('SET', KEYS[1], cjson.encode(datos), 'EX', ARGV[2])
redis.call('SET', KEYS[2], ARGV[1], 'EX', ARGV[2])
f.revocada = '0'
redis.call('SET', KEYS[3], cjson.encode(f), 'EX', ARGV[2])
return {'OK', datos.id_usuario, datos.family}
"""


def _clave_token(token: str) -> str:
    return f"refresh:tok:{sha256_hex(token)}"


def _clave_familia(family_id: str) -> str:
    return f"refresh:family:{family_id}"


def _clave_usuario(id_usuario: UUID | str) -> str:
    return f"refresh:user:{id_usuario}"


async def crear_sesion(redis: Redis, id_usuario: UUID) -> tuple[str, str]:
    """Crea una familia nueva y devuelve `(refresh_token, family_id)`."""
    family_id = str(uuid4())
    token = generate_opaque_token()
    pipe = redis.pipeline()
    pipe.set(
        _clave_token(token),
        json.dumps({"id_usuario": str(id_usuario), "family": family_id, "usado": "0"}),
        ex=TTL,
    )
    pipe.set(
        _clave_familia(family_id),
        json.dumps({"id_usuario": str(id_usuario), "revocada": "0"}),
        ex=TTL,
    )
    pipe.sadd(_clave_usuario(id_usuario), family_id)
    pipe.expire(_clave_usuario(id_usuario), TTL)
    await pipe.execute()
    return token, family_id


async def datos_de_token(redis: Redis, token: str) -> dict[str, str] | None:
    crudo = await redis.get(_clave_token(token))
    if crudo is None:
        return None
    datos: dict[str, str] = json.loads(crudo)
    return datos


async def rotar(redis: Redis, token: str) -> Rotacion:
    datos = await datos_de_token(redis, token)
    if datos is None:
        return Rotacion(EstadoRotacion.INVALIDO)

    id_usuario = UUID(datos["id_usuario"])
    family_id = datos["family"]

    if datos.get("usado") == "1":
        await revocar_familia(redis, family_id)
        return Rotacion(EstadoRotacion.REUSO, id_usuario=id_usuario, family_id=family_id)

    nuevo = generate_opaque_token()
    payload = json.dumps({"id_usuario": str(id_usuario), "family": family_id, "usado": "0"})
    resultado = await cast(
        Awaitable[Any],
        redis.eval(
            _SCRIPT_ROTAR,
            3,
            _clave_token(token),
            _clave_token(nuevo),
            _clave_familia(family_id),
            payload,
            str(TTL),
        ),
    )
    estado = EstadoRotacion(resultado[0])
    if estado is EstadoRotacion.OK:
        return Rotacion(
            estado,
            refresh_token=nuevo,
            id_usuario=id_usuario,
            family_id=family_id,
        )
    return Rotacion(estado, id_usuario=id_usuario, family_id=family_id)


async def revocar_familia(redis: Redis, family_id: str) -> None:
    clave = _clave_familia(family_id)
    crudo = await redis.get(clave)
    datos = json.loads(crudo) if crudo else {"revocada": "0"}
    datos["revocada"] = "1"
    await cast(Awaitable[Any], redis.set(clave, json.dumps(datos), ex=TTL))


async def revocar_sesiones_usuario(redis: Redis, id_usuario: UUID) -> None:
    """Revoca todas las familias abiertas del usuario (C2)."""
    familias = await cast(Awaitable[set[str]], redis.smembers(_clave_usuario(id_usuario)))
    for family_id in familias:
        await revocar_familia(redis, str(family_id))
