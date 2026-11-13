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


@router.get("/ready", summary="Readiness check")
async def ready(session: SessionDep) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
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

    return {"status": "ready"}
