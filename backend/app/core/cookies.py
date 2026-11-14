"""Emisión y borrado de las cookies de sesión.

`refresh_token` es `httpOnly` (el JS nunca la lee) y solo viaja a
`/api/v1/auth`. `csrf_token` es legible por el cliente para poder mandarla en
`X-CSRF-Token` (double-submit) y viaja a toda la API.
"""

from fastapi import Response

from app.core.config import get_settings

settings = get_settings()

MAX_AGE = settings.refresh_token_expire_days * 24 * 60 * 60
DOMINIO = settings.cookie_domain or None


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=MAX_AGE,
        path=settings.refresh_cookie_path,
        domain=DOMINIO,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
    )


def set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=token,
        max_age=MAX_AGE,
        path=settings.csrf_cookie_path,
        domain=DOMINIO,
        secure=settings.cookie_secure,
        httponly=False,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.refresh_cookie_path,
        domain=DOMINIO,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
    )
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        path=settings.csrf_cookie_path,
        domain=DOMINIO,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
    )
