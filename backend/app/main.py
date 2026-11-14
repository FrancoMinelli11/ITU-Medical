from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_error_handler,
)
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware
from app.db.session import dispose_engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.app_debug,
        lifespan=lifespan,
        description="API de gestión administrativa de turnos médicos.",
    )
    app.state.request_id_header = settings.request_id_header

    # El orden de `add_middleware` es inverso al de ejecución: el último
    # agregado corre primero. Resultado (afuera → adentro):
    # RequestID → CORS → TrustedHost → router.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts_list)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[settings.request_id_header, "Retry-After"],
    )
    app.add_middleware(RequestIDMiddleware)

    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"name": settings.app_name, "docs": "/docs", "api": settings.api_v1_prefix}

    return app


app = create_app()
