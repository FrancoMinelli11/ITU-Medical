"""CSRF double-submit (S-10, RNF-01).

La cookie `csrf_token` viaja en claro (legible por el SPA) y cada mutación debe
repetir su valor en el header `X-CSRF-Token`. Un sitio externo puede forzar el
envío de cookies, pero no puede leer la cookie para armar el header.

Se implementa como **dependencia global del router** y no como middleware: así
el chequeo corre después del ruteo y un `POST` a una ruta solo-GET sigue dando
405 (y no 403). Al estar declarada una sola vez en `api_router`, todo endpoint
nuevo queda protegido por defecto en lugar de depender de que alguien se acuerde
de agregar el decorador.

Sin `Origin`/`Referer` no se valida nada más: el double-submit ya impide el
ataque, y exigir `Origin` rompería clientes legítimos (curl, tests, apps nativas).
"""

from __future__ import annotations

import hmac

import structlog
from starlette.requests import Request

from app.core.config import get_settings
from app.core.exceptions import ApiError

settings = get_settings()
logger = structlog.get_logger(__name__)

METODOS_MUTANTES = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Rutas (relativas a `api_v1_prefix`) que no exigen CSRF porque el usuario aún
# no tiene sesión: son el punto de entrada o de recuperación de credenciales.
RUTAS_EXENTAS = frozenset(
    {
        "/auth/login",
        "/auth/registro",
        "/auth/recuperar-password",
        "/auth/restablecer-password",
        "/auth/verificar-email",
        "/auth/reenviar-verificacion",
    }
)


def requiere_csrf(method: str, path: str) -> bool:
    if method.upper() not in METODOS_MUTANTES:
        return False
    if not path.startswith(settings.api_v1_prefix):
        return False
    relativa = path[len(settings.api_v1_prefix) :].rstrip("/") or "/"
    return relativa not in RUTAS_EXENTAS


async def verificar_csrf(request: Request) -> None:
    if not requiere_csrf(request.method, request.url.path):
        return

    cookie = request.cookies.get(settings.csrf_cookie_name)
    header = request.headers.get(settings.csrf_header_name)

    motivo: str | None = None
    if not cookie or not header:
        motivo = "faltante"
    elif not hmac.compare_digest(cookie.encode(), header.encode()):
        motivo = "no_coincide"

    if motivo is not None:
        logger.warning(
            "csrf_rechazado",
            motivo=motivo,
            method=request.method,
            path=request.url.path,
        )
        raise ApiError(
            403,
            "CSRF_INVALIDO",
            "Solicitud rechazada",
            "Falta el token CSRF o no coincide con la cookie.",
            headers={"Cache-Control": "no-store"},
        )
