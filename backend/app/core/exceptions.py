from typing import Any, cast
from uuid import uuid4

import structlog
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger(__name__)


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        title: str,
        detail: str,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.title = title
        self.detail = detail
        self.errors = errors or []


def problem_response(
    request: Request,
    status_code: int,
    code: str,
    title: str,
    detail: str,
    errors: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    payload: dict[str, Any] = {
        "type": f"https://api.turnos.local/problems/{code.lower().replace('_', '-')}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": request.url.path,
        "code": code,
        "request_id": request_id,
    }
    if errors:
        payload["errors"] = errors
    response_headers = {getattr(request.app.state, "request_id_header", "X-Request-ID"): request_id}
    if headers:
        response_headers.update(headers)
    return JSONResponse(
        status_code=status_code,
        content=payload,
        media_type="application/problem+json",
        headers=response_headers,
    )


async def api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(ApiError, exc)
    return problem_response(
        request,
        error.status_code,
        error.code,
        error.title,
        error.detail,
        error.errors,
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    validation_error = cast(RequestValidationError, exc)
    errors = [
        {
            "field": ".".join(str(part) for part in error.get("loc", ())),
            "message": error.get("msg", "Valor inválido"),
            "type": error.get("type", "value_error"),
        }
        for error in validation_error.errors()
    ]
    return problem_response(
        request,
        status.HTTP_400_BAD_REQUEST,
        "VALIDACION",
        "Datos inválidos",
        "Revisá los campos señalados.",
        errors,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", error=str(exc), path=request.url.path)
    return problem_response(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "ERROR_INTERNO",
        "Error interno",
        "Ocurrió un error inesperado.",
    )


# Códigos estables para los errores que genera Starlette/FastAPI.
CODIGOS_HTTP: dict[int, tuple[str, str]] = {
    400: ("SOLICITUD_INVALIDA", "Solicitud inválida"),
    401: ("NO_AUTENTICADO", "No autenticado"),
    403: ("SIN_PERMISO", "Sin permiso"),
    404: ("NO_ENCONTRADO", "Recurso no encontrado"),
    405: ("METODO_NO_PERMITIDO", "Método no permitido"),
    406: ("NO_ACEPTABLE", "Formato no aceptable"),
    409: ("CONFLICTO", "Conflicto"),
    422: ("VALIDACION", "Datos inválidos"),
    429: ("DEMASIADAS_SOLICITUDES", "Demasiadas solicitudes"),
    500: ("ERROR_INTERNO", "Error interno"),
    503: ("SERVICIO_NO_DISPONIBLE", "Servicio no disponible"),
}


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Normaliza los errores de Starlette/FastAPI al formato RFC 7807."""
    error = cast(StarletteHTTPException, exc)
    code, title = CODIGOS_HTTP.get(error.status_code, ("ERROR_HTTP", "Error"))
    detail = error.detail if isinstance(error.detail, str) else title
    headers = dict(error.headers) if error.headers else None
    return problem_response(
        request,
        error.status_code,
        code,
        title,
        detail,
        headers=headers,
    )
