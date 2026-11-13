from arq import cron

from app.workers.arq_settings import WorkerSettings as BaseWorkerSettings


async def recordatorios(ctx: dict[str, object]) -> None:
    """Punto de entrada del job de recordatorios (FASE 3)."""
    return None


class WorkerSettings(BaseWorkerSettings):
    cron_jobs = [
        cron(recordatorios, hour=8, minute=0, run_at_startup=False),
    ]
