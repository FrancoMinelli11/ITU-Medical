import asyncio
import smtplib
from typing import Any

from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.core.exceptions import ApiError

router = APIRouter(tags=["sistema"])
settings = get_settings()


@router.get("/health", summary="Health check")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _probar_smtp() -> None:
    with smtplib.SMTP(
        settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
    ) as smtp:
        smtp.noop()


async def _smtp_disponible() -> bool:
    """Chequeo no bloqueante: un fallo de correo no puede tumbar `/ready`.

    El envío es asíncrono (RNF-11) y su fallo no impide iniciar sesión ni
    reservar. Si mailpit está caído, `checks.smtp` queda en `error` pero el
    código de estado sigue siendo 200.
    """
    try:
        await asyncio.wait_for(
            asyncio.to_thread(_probar_smtp),
            timeout=settings.smtp_timeout_seconds + 0.5,
        )
    except (OSError, smtplib.SMTPException, TimeoutError):
        return False
    return True


@router.get("/ready", summary="Readiness check")
async def ready(session: SessionDep) -> dict[str, Any]:
    try:
        await session.execute(text("SELECT 1"))
    # `OSError` cubre los fallos de resolución DNS y de conexión que asyncpg
    # levanta antes de que SQLAlchemy los envuelva (p. ej. `socket.gaierror`
    # cuando el contenedor de la base está detenido).
    except (SQLAlchemyError, OSError) as exc:
        raise ApiError(
            503, "BASE_NO_DISPONIBLE", "Servicio no disponible", "La base de datos no responde."
        ) from exc

    redis = Redis.from_url(settings.redis_url)
    try:
        await redis.ping()
    except Exception as exc:
        raise ApiError(
            503, "REDIS_NO_DISPONIBLE", "Servicio no disponible", "Redis no responde."
        ) from exc
    finally:
        await redis.aclose()

    # Los DB lógicos de rate limit y refresh viven en el mismo servidor Redis
    # que se acaba de verificar; un chequeo aparte no agregaría información.
    smtp_ok = await _smtp_disponible()
    return {
        "status": "ready",
        "checks": {
            "database": "ok",
            "redis": "ok",
            "smtp": "ok" if smtp_ok else "error",
        },
    }
