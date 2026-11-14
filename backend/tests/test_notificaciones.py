"""RF-22, RNF-11 y P-42: envío asíncrono, reintentos e idempotencia."""

from __future__ import annotations

import socket
from uuid import UUID

import pytest
from arq import Retry
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models.enums import EstadoNotificacion, TipoNotificacion
from app.db.models.notificacion import Notificacion
from app.db.session import SessionLocal
from app.services import email_service, notificacion_service
from app.workers import notificaciones
from app.workers.notificaciones import enviar_email

settings = get_settings()
PASSWORD = "Password123!"


def _exigir_smtp() -> None:
    try:
        with socket.create_connection((settings.smtp_host, settings.smtp_port), timeout=2):
            pass
    except OSError as exc:  # pragma: no cover - depende del entorno
        pytest.skip(f"SMTP no disponible en {settings.smtp_host}:{settings.smtp_port}: {exc}")


async def _crear_notificacion(usuario) -> UUID:
    async with SessionLocal() as session:
        notificacion = notificacion_service.crear(
            session, usuario=usuario, tipo=TipoNotificacion.VERIFICACION_EMAIL
        )
        await session.commit()
        return notificacion.id_notificacion


async def _leer(id_notificacion: UUID) -> Notificacion:
    async with SessionLocal() as session:
        fila = await session.get(Notificacion, id_notificacion)
        assert fila is not None
        return fila


async def test_worker_envia_y_marca_enviada(client, fabrica) -> None:
    _exigir_smtp()
    usuario = await fabrica.crear(password=PASSWORD)
    id_notificacion = await _crear_notificacion(usuario)

    resultado = await enviar_email(
        {}, str(id_notificacion), usuario.email, "Asunto de prueba", "Cuerpo de prueba"
    )

    assert resultado == "enviada"
    fila = await _leer(id_notificacion)
    assert fila.estado == EstadoNotificacion.ENVIADA
    assert fila.intentos == 1
    assert fila.fecha_envio is not None
    assert fila.ultimo_error is None


async def test_worker_es_idempotente(client, fabrica) -> None:
    usuario = await fabrica.crear(password=PASSWORD)
    id_notificacion = await _crear_notificacion(usuario)

    async with SessionLocal() as session:
        fila = await session.get(Notificacion, id_notificacion)
        assert fila is not None
        fila.estado = EstadoNotificacion.ENVIADA
        await session.commit()

    resultado = await enviar_email({}, str(id_notificacion), usuario.email, "Asunto", "Cuerpo")

    assert resultado == "ya_enviada"
    fila = await _leer(id_notificacion)
    assert fila.intentos == 0


async def test_worker_reintenta_y_termina_en_fallida(
    client, fabrica, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RNF-11: 3 intentos con backoff 60, 300 y 900 segundos."""
    usuario = await fabrica.crear(password=PASSWORD)
    id_notificacion = await _crear_notificacion(usuario)

    def _romper(*args: object, **kwargs: object) -> None:
        raise OSError("smtp caído")

    monkeypatch.setattr(email_service, "enviar", _romper)

    with pytest.raises(Retry) as primer_fallo:
        await enviar_email({}, str(id_notificacion), usuario.email, "Asunto", "Cuerpo")
    assert primer_fallo.value.defer_score == 60_000
    fila = await _leer(id_notificacion)
    assert fila.estado == EstadoNotificacion.PENDIENTE
    assert fila.intentos == 1

    with pytest.raises(Retry) as segundo_fallo:
        await enviar_email({}, str(id_notificacion), usuario.email, "Asunto", "Cuerpo")
    assert segundo_fallo.value.defer_score == 300_000

    resultado = await enviar_email({}, str(id_notificacion), usuario.email, "Asunto", "Cuerpo")

    assert resultado == "fallida"
    fila = await _leer(id_notificacion)
    assert fila.estado == EstadoNotificacion.FALLIDA
    assert fila.intentos == 3
    assert "OSError" in (fila.ultimo_error or "")


async def test_notificacion_inexistente_no_explota(client) -> None:
    resultado = await enviar_email(
        {},
        "00000000-0000-0000-0000-000000000000",
        "nadie@example.com",
        "Asunto",
        "Cuerpo",
    )

    assert resultado == "sin_notificacion"


async def test_el_fallo_de_encolado_no_aborta_la_operacion(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RNF-11: si Redis está caído, el alta igual se confirma."""

    async def _sin_redis(*args: object, **kwargs: object) -> None:
        raise ConnectionError("redis caído")

    monkeypatch.setattr(notificacion_service, "create_pool", _sin_redis)

    respuesta = await client.post(
        "/api/v1/auth/registro",
        json={
            "dni": "30999888",
            "email": "sin.cola@example.com",
            "password": PASSWORD,
            "nombre": "Sin",
            "apellido": "Cola",
        },
    )

    assert respuesta.status_code == 201, respuesta.text

    async with SessionLocal() as session:
        notificacion = await session.scalar(
            select(Notificacion).where(
                Notificacion.id_usuario_destinatario == UUID(respuesta.json()["id_usuario"])
            )
        )
        assert notificacion is not None
        assert notificacion.estado == EstadoNotificacion.PENDIENTE


def test_el_worker_declara_el_maximo_de_intentos() -> None:
    assert notificaciones.MAX_INTENTOS == 3
    assert notificaciones.ESPERAS == (60, 300, 900)
