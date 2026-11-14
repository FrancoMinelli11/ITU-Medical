from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.notificaciones import enviar_email

settings = get_settings()


async def ping(ctx: dict[str, object]) -> str:
    return "pong"


class WorkerSettings:
    functions = [enviar_email, ping]
    redis_settings = RedisSettings.from_dsn(settings.arq_redis_url)
