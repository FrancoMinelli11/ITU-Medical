"""Endpoints de identidad y sesión (RF-03, RF-27, RN-29, RN-30, RN-37)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request, Response, status

from app.api.deps import CurrentUser, RateLimitRedisDep, RefreshRedisDep, SessionDep
from app.core.config import get_settings
from app.core.cookies import clear_auth_cookies, set_csrf_cookie, set_refresh_cookie
from app.core.exceptions import ApiError
from app.core.security import create_access_token, generate_csrf_token
from app.db.models.usuario import Usuario
from app.schemas.auth import LoginRequest, LoginResponse, RefreshResponse, UsuarioOut
from app.services import auditoria_service, auth_service, refresh_service
from app.services.auditoria_service import Accion
from app.services.refresh_service import EstadoRotacion

router = APIRouter()
settings = get_settings()

EXPIRES_IN = settings.access_token_expire_minutes * 60

SESION_INVALIDA = (
    401,
    "SESION_INVALIDA",
    "Sesión inválida",
    "Tu sesión venció. Iniciá sesión de nuevo.",
)


def _sesion_invalida() -> ApiError:
    return ApiError(*SESION_INVALIDA, limpiar_cookies=True)


@router.get(
    "/csrf",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Emitir la cookie CSRF (bootstrap del SPA)",
)
async def obtener_csrf(response: Response) -> None:
    set_csrf_cookie(response, generate_csrf_token())


@router.post("/login", response_model=LoginResponse, summary="Iniciar sesión")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    redis_rate: RateLimitRedisDep,
    redis_refresh: RefreshRedisDep,
) -> LoginResponse:
    usuario = await auth_service.autenticar(
        session=session,
        redis=redis_rate,
        dni=payload.dni,
        password=payload.password,
        request=request,
    )

    refresh_token, family_id = await refresh_service.crear_sesion(redis_refresh, usuario.id_usuario)
    access_token = create_access_token(
        usuario.id_usuario, {"rol": usuario.rol.value, "sid": family_id}
    )

    set_refresh_cookie(response, refresh_token)
    set_csrf_cookie(response, generate_csrf_token())

    return LoginResponse(
        access_token=access_token,
        expires_in=EXPIRES_IN,
        usuario=await auth_service.perfil(session, usuario),
        debe_cambiar_password=usuario.debe_cambiar_password,
    )


@router.post("/refresh", response_model=RefreshResponse, summary="Renovar el token de acceso")
async def refresh(
    request: Request,
    response: Response,
    session: SessionDep,
    redis: RefreshRedisDep,
) -> RefreshResponse:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise ApiError(
            401,
            "NO_AUTENTICADO",
            "No autenticado",
            "No hay una sesión para renovar.",
            limpiar_cookies=True,
        )

    rotacion = await refresh_service.rotar(redis, token)
    if rotacion.estado is not EstadoRotacion.OK or rotacion.refresh_token is None:
        if rotacion.estado is EstadoRotacion.REUSO:
            await auditoria_service.registrar(
                session,
                accion=Accion.REFRESH_REUTILIZADO,
                id_usuario=rotacion.id_usuario,
                datos_despues={"familia": rotacion.family_id},
                request=request,
            )
        raise _sesion_invalida()

    assert rotacion.id_usuario is not None  # garantizado por el estado OK
    usuario = await session.get(Usuario, rotacion.id_usuario)
    if usuario is None or not usuario.habilitado:
        if rotacion.family_id:
            await refresh_service.revocar_familia(redis, rotacion.family_id)
        raise _sesion_invalida()

    access_token = create_access_token(
        usuario.id_usuario, {"rol": usuario.rol.value, "sid": rotacion.family_id}
    )
    set_refresh_cookie(response, rotacion.refresh_token)
    # El valor de CSRF rota junto con el refresh: un token filtrado deja de
    # servir después de la primera renovación.
    set_csrf_cookie(response, generate_csrf_token())

    await auditoria_service.registrar(
        session,
        accion=Accion.REFRESH,
        id_usuario=usuario.id_usuario,
        request=request,
    )

    return RefreshResponse(
        access_token=access_token,
        expires_in=EXPIRES_IN,
        usuario=await auth_service.perfil(session, usuario),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cerrar sesión",
)
async def logout(
    request: Request,
    response: Response,
    session: SessionDep,
    redis: RefreshRedisDep,
) -> None:
    """Idempotente: revoca la familia del refresh y limpia las cookies.

    No exige un access token válido a propósito: si el usuario deja la pestaña
    abierta más de 15 minutos, el token de acceso vence y un logout con 401
    dejaría el refresh vivo (la sesión "reviviría" en la próxima recarga).
    """
    id_usuario: UUID | None = None
    token = request.cookies.get(settings.refresh_cookie_name)
    if token:
        datos = await refresh_service.datos_de_token(redis, token)
        if datos is not None:
            id_usuario = UUID(datos["id_usuario"])
            await refresh_service.revocar_familia(redis, datos["family"])

    clear_auth_cookies(response)

    if id_usuario is not None:
        await auditoria_service.registrar(
            session,
            accion=Accion.LOGOUT,
            id_usuario=id_usuario,
            request=request,
        )


@router.get("/me", response_model=UsuarioOut, summary="Perfil del usuario autenticado")
async def me(usuario: CurrentUser, session: SessionDep) -> UsuarioOut:
    """C3: responde 200 aunque `debe_cambiar_password` sea `true`.

    Es lo primero que consulta el SPA al montar; si devolviera 403 no podría
    distinguir "sesión inválida" de "tenés que cambiar la contraseña".
    """
    return await auth_service.perfil(session, usuario)
