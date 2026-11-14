from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.arq_settings import ping

settings = get_settings()


async def recordatorios(ctx: dict[str, object]) -> None:
    """Punto de entrada del job de recordatorios (FASE 3)."""
    return None


class WorkerSettings:
    """Configuración del worker de cron.

    No hereda de `arq_settings.WorkerSettings` a propósito: arq 0.28 lee
    `settings_cls.__dict__` (no recorre la MRO) para extraer los argumentos del
    `Worker`, así que los atributos heredados se pierden y el proceso arranca
    con `RedisSettings()` por defecto (localhost:6379) y sin funciones.
    Por eso `functions` y `redis_settings` se declaran acá de forma explícita.
    """

    functions = [recordatorios, ping]
    redis_settings = RedisSettings.from_dsn(settings.arq_redis_url)
    cron_jobs = [
        cron(recordatorios, hour=8, minute=0, run_at_startup=False),
    ]
