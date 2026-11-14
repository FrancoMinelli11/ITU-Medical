"""`/ready` distingue lo que impide operar de lo que solo degrada.

RNF-11: el correo es asíncrono, así que un mailpit caído **no** saca la API de
rotación; la base y Redis sí.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import OperationalError

from app.api.v1.endpoints import system
from app.db.session import get_session
from app.main import app


class _SesionCaida:
    """Sustituto de `AsyncSession` cuyo `execute` siempre falla."""

    async def execute(self, *_args: object, **_kwargs: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("conexión perdida"))


async def test_ready_ok(client) -> None:
    respuesta = await client.get("/api/v1/ready")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "status": "ready",
        "checks": {"database": "ok", "redis": "ok", "smtp": "ok"},
    }


async def test_ready_sin_base(client) -> None:
    app.dependency_overrides[get_session] = lambda: _SesionCaida()
    try:
        respuesta = await client.get("/api/v1/ready")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert respuesta.status_code == 503
    assert respuesta.headers["content-type"] == "application/problem+json"
    assert respuesta.json()["code"] == "BASE_NO_DISPONIBLE"


async def test_ready_sin_redis(client, monkeypatch) -> None:
    # Puerto cerrado: la conexión se rechaza sin esperar el timeout.
    monkeypatch.setattr(system.settings, "redis_url", "redis://localhost:6399/0")

    respuesta = await client.get("/api/v1/ready")

    assert respuesta.status_code == 503
    assert respuesta.json()["code"] == "REDIS_NO_DISPONIBLE"


@pytest.mark.parametrize("puerto", [1, 6399], ids=["rechazado", "cerrado"])
async def test_ready_sin_smtp_sigue_ready(client, monkeypatch, puerto: int) -> None:
    monkeypatch.setattr(system.settings, "smtp_port", puerto)
    monkeypatch.setattr(system.settings, "smtp_timeout_seconds", 0.5)

    respuesta = await client.get("/api/v1/ready")

    assert respuesta.status_code == 200
    assert respuesta.json()["checks"]["smtp"] == "error"
    assert respuesta.json()["checks"]["database"] == "ok"
