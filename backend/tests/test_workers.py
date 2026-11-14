"""Regresión: arq descubre la configuración leyendo `WorkerSettings.__dict__`.

`arq.worker.get_kwargs` no recorre la MRO, así que una subclase que solo declare
`cron_jobs` pierde `functions` y `redis_settings` heredados. El proceso arranca
entonces con `RedisSettings()` por defecto (localhost:6379) y sin funciones, y
entra en crash loop dentro de docker compose.
"""

import pytest
from arq.connections import RedisSettings
from arq.worker import get_kwargs

from app.core.config import get_settings
from app.workers.arq_settings import WorkerSettings as SettingsWorker
from app.workers.scheduler import WorkerSettings as SchedulerWorker

CONFIGURACIONES = [SettingsWorker, SchedulerWorker]


@pytest.mark.parametrize("settings_cls", CONFIGURACIONES)
def test_arq_encuentra_funciones_y_redis(settings_cls: type) -> None:
    argumentos = get_kwargs(settings_cls)
    assert "functions" in argumentos
    assert "redis_settings" in argumentos


@pytest.mark.parametrize("settings_cls", CONFIGURACIONES)
def test_redis_apunta_a_la_url_configurada(settings_cls: type) -> None:
    actual = get_kwargs(settings_cls)["redis_settings"]
    esperado = RedisSettings.from_dsn(get_settings().arq_redis_url)
    assert actual == esperado


def test_scheduler_registra_su_cron() -> None:
    argumentos = get_kwargs(SchedulerWorker)
    nombres = {funcion.__name__ for funcion in argumentos["functions"]}
    assert "recordatorios" in nombres
    assert argumentos["cron_jobs"]
