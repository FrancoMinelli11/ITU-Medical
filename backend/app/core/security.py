import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings

settings = get_settings()
_password_hasher = PasswordHasher(
    time_cost=settings.argon2_time_cost,
    memory_cost=settings.argon2_memory_cost,
    parallelism=settings.argon2_parallelism,
)

# Hash de costo equivalente al de una cuenta real. Se calcula una única vez al
# importar el módulo para que el login tarde lo mismo cuando el DNI no existe:
# sin esto, un atacante enumeraría DNIs midiendo tiempos de respuesta.
_PASSWORD_DUMMY = "hash-dummy-para-uniformar-el-tiempo-de-login"
DUMMY_PASSWORD_HASH = _password_hasher.hash(_PASSWORD_DUMMY)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False


def verify_password_or_dummy(password: str, password_hash: str | None) -> bool:
    """Verifica contra `password_hash` o, si es `None`, contra el hash dummy.

    En ambos caminos se ejecuta argon2id exactamente una vez, así que un DNI
    inexistente no se distingue de uno existente por tiempo de respuesta.
    """
    if password_hash is None:
        verify_password(password, DUMMY_PASSWORD_HASH)
        return False
    return verify_password(password, password_hash)


def sha256_hex(value: str) -> str:
    """Hash con el que se persisten los tokens opacos (nunca el token plano)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_opaque_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(subject: UUID | str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
