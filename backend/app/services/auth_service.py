"""Reglas de autenticación (RF-03, RN-26..RN-30, S-12).

El login no distingue "DNI inexistente" de "contraseña incorrecta" ni de
"cuenta deshabilitada": los tres casos devuelven 401 `CREDENCIALES_INVALIDAS`,
con argon2id ejecutado exactamente una vez en todos los caminos (C1). La causa
real queda en `AUDITORIA`, nunca en la respuesta.
"""

from __future__ import annotations

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config import get_settings
from app.core.exceptions import ApiError
from app.core.http import ip_de_request
from app.core.rate_limit import RateLimiter, verificar_limites
from app.core.security import verify_password_or_dummy
from app.core.timezone import now_utc
from app.db.models.enums import RolUsuario
from app.db.models.paciente import Paciente
from app.db.models.usuario import Usuario
from app.schemas.auth import UsuarioOut
from app.services import auditoria_service
from app.services.auditoria_service import Accion

settings = get_settings()

CREDENCIALES_INVALIDAS = (
    401,
    "CREDENCIALES_INVALIDAS",
    "Credenciales inválidas",
    "DNI o contraseña incorrectos.",
)


def _error_credenciales() -> ApiError:
    return ApiError(*CREDENCIALES_INVALIDAS)


async def autenticar(
    *,
    session: AsyncSession,
    redis: Redis,
    dni: str,
    password: str,
    request: Request,
) -> Usuario:
    ip = ip_de_request(request) or "desconocida"
    limite_dni = RateLimiter(redis, prefijo="login:dni", limite=settings.rate_limit_login_dni)
    limite_ip = RateLimiter(redis, prefijo="login:ip", limite=settings.rate_limit_login_ip)

    # P-36: el bloqueo se evalúa antes de tocar argon2id.
    await verificar_limites((limite_dni, dni), (limite_ip, ip))

    usuario = await session.scalar(select(Usuario).where(Usuario.dni == dni))
    correcta = verify_password_or_dummy(password, usuario.password_hash if usuario else None)

    async def registrar_fallo(motivo: str) -> None:
        await limite_dni.registrar(dni)
        await limite_ip.registrar(ip)
        await auditoria_service.registrar(
            session,
            accion=Accion.LOGIN_FALLIDO,
            id_usuario=usuario.id_usuario if usuario is not None else None,
            datos_despues={"motivo": motivo, "dni": dni},
            request=request,
        )

    if usuario is None:
        await registrar_fallo("USUARIO_INEXISTENTE")
        raise _error_credenciales()

    if not correcta:
        await registrar_fallo("PASSWORD_INCORRECTA")
        raise _error_credenciales()

    if not usuario.habilitado:
        # La contraseña era correcta, pero la cuenta está dada de baja: mismo
        # 401 hacia afuera para no confirmar que el DNI existe.
        await registrar_fallo("CUENTA_DESHABILITADA")
        raise _error_credenciales()

    await limite_dni.reiniciar(dni)
    usuario.ultimo_login = now_utc()
    await session.commit()
    await auditoria_service.registrar(
        session,
        accion=Accion.LOGIN_EXITOSO,
        id_usuario=usuario.id_usuario,
        datos_despues={"rol": usuario.rol.value, "dni": usuario.dni},
        request=request,
    )
    return usuario


async def perfil(session: AsyncSession, usuario: Usuario) -> UsuarioOut:
    telefono: str | None = None
    fecha_nacimiento = None
    if usuario.rol is RolUsuario.PACIENTE:
        paciente = await session.scalar(
            select(Paciente).where(Paciente.id_usuario == usuario.id_usuario)
        )
        if paciente is not None:
            telefono = paciente.telefono
            fecha_nacimiento = paciente.fecha_nacimiento

    return UsuarioOut(
        id_usuario=usuario.id_usuario,
        dni=usuario.dni,
        email=usuario.email,
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        rol=usuario.rol,
        email_verificado=usuario.email_verificado,
        debe_cambiar_password=usuario.debe_cambiar_password,
        ultimo_login=usuario.ultimo_login,
        telefono=telefono,
        fecha_nacimiento=fecha_nacimiento,
    )
