from __future__ import annotations

import structlog
from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.recordatorio_service import procesar_recordatorios_24h
from app.workers.arq_settings import ping

logger = structlog.get_logger(__name__)
settings = get_settings()


async def recordatorios(ctx: dict[str, object]) -> int:
    """Job periódico para el envío de recordatorios 24hs antes del turno (RF-22, P-39)."""
    async with SessionLocal() as session:
        try:
            total = await procesar_recordatorios_24h(session)
            logger.info("recordatorios_procesados", total=total)
            return total
        except Exception:
            logger.exception("error_procesando_recordatorios")
            return 0


class WorkerSettings:
    """Configuración del worker de cron para tareas programadas."""

    functions = [recordatorios, ping]
    redis_settings = RedisSettings.from_dsn(settings.arq_redis_url)
    cron_jobs = [
        # Ejecución cada 15 minutos para detectar turnos en la ventana de 24 hs
        cron(recordatorios, minute={0, 15, 30, 45}, run_at_startup=False),
    ]
