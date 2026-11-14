"""Helpers de request compartidos por auth, rate limit y auditoría."""

from __future__ import annotations

import ipaddress

from starlette.requests import Request


def ip_de_request(request: Request) -> str | None:
    """IP del cliente o `None` si no es una IP válida.

    No se confía en `X-Forwarded-For`: sin un proxy propio configurado sería
    trivial falsear la clave del rate limit. En desarrollo el proxy de Vite
    aparece como `127.0.0.1`, que es suficiente para el límite por IP.
    """
    if request.client is None:
        return None
    host = request.client.host
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return None
    return host
