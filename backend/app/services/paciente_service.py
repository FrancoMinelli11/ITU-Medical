"""Alta y mantenimiento de pacientes (RF-01, RF-02, CU-01, CU-02)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.exceptions import ApiError
from app.core.security import hash_password
from app.db.models.enums import RolUsuario
from app.db.models.notificacion import Notificacion
from app.db.models.paciente import Paciente
from app.db.models.usuario import Usuario
from app.schemas.auth import RegistroRequest
from app.schemas.common import Pagina
from app.schemas.paciente import PacienteCreate, PacienteOut, PacienteUpdate
from app.services import auditoria_service, verificacion_service
from app.services.auditoria_service import Accion

DNI_DUPLICADO = (
    409,
    "DNI_DUPLICADO",
    "Datos ya registrados",
    "Ya existe una cuenta con ese DNI.",
)
EMAIL_DUPLICADO = (
    409,
    "EMAIL_DUPLICADO",
    "Datos ya registrados",
    "Ya existe una cuenta con ese correo electrónico.",
)


def _salida(paciente: Paciente, usuario: Usuario) -> PacienteOut:
    return PacienteOut(
        id_paciente=paciente.id_paciente,
        id_usuario=usuario.id_usuario,
        dni=usuario.dni,
        email=usuario.email,
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        telefono=paciente.telefono,
        fecha_nacimiento=paciente.fecha_nacimiento,
        email_verificado=usuario.email_verificado,
        habilitado=usuario.habilitado,
        debe_cambiar_password=usuario.debe_cambiar_password,
        fecha_creacion=paciente.fecha_creacion,
    )


async def _verificar_unicidad(
    session: AsyncSession, *, dni: str, email: str, id_usuario: UUID | None = None
) -> None:
    consulta_dni = select(Usuario.id_usuario).where(Usuario.dni == dni)
    if id_usuario is not None:
        consulta_dni = consulta_dni.where(Usuario.id_usuario != id_usuario)
    if await session.scalar(consulta_dni) is not None:
        raise ApiError(*DNI_DUPLICADO)

    consulta_email = select(Usuario.id_usuario).where(Usuario.email == email)
    if id_usuario is not None:
        consulta_email = consulta_email.where(Usuario.id_usuario != id_usuario)
    if await session.scalar(consulta_email) is not None:
        raise ApiError(*EMAIL_DUPLICADO)


async def registrar_web(
    session: AsyncSession, *, payload: RegistroRequest, request: Request
) -> tuple[PacienteOut, Notificacion, str, str]:
    """RF-01: cuenta sin verificar + correo de verificación.

    Devuelve el paciente, la notificación pendiente y el asunto/cuerpo a
    encolar. La transacción queda confirmada acá: el encolado es *best effort*
    (RNF-11).
    """
    await _verificar_unicidad(session, dni=payload.dni, email=payload.email)

    usuario = Usuario(
        dni=payload.dni,
        email=payload.email,
        password_hash=hash_password(payload.password),
        rol=RolUsuario.PACIENTE,
        nombre=payload.nombre,
        apellido=payload.apellido,
        email_verificado=False,
        debe_cambiar_password=False,
    )
    session.add(usuario)
    await session.flush()
    paciente = Paciente(
        id_usuario=usuario.id_usuario,
        telefono=payload.telefono,
        fecha_nacimiento=payload.fecha_nacimiento,
    )
    session.add(paciente)
    await session.flush()

    notificacion, asunto, cuerpo = await verificacion_service.emitir(
        session, usuario=usuario, request=request
    )
    await auditoria_service.registrar(
        session,
        accion=Accion.ALTA_PACIENTE_WEB,
        id_usuario=usuario.id_usuario,
        datos_despues={"dni": usuario.dni, "email": usuario.email, "origen": "WEB"},
        request=request,
        commit=False,
    )
    await session.commit()
    return _salida(paciente, usuario), notificacion, asunto, cuerpo


async def crear_desde_recepcion(
    session: AsyncSession, *, payload: PacienteCreate, request: Request
) -> PacienteOut:
    """RF-02: la contraseña inicial es el DNI y el correo queda verificado."""
    await _verificar_unicidad(session, dni=payload.dni, email=payload.email)

    usuario = Usuario(
        dni=payload.dni,
        email=payload.email,
        password_hash=hash_password(payload.dni),
        rol=RolUsuario.PACIENTE,
        nombre=payload.nombre,
        apellido=payload.apellido,
        email_verificado=True,
        debe_cambiar_password=True,
    )
    session.add(usuario)
    await session.flush()
    paciente = Paciente(
        id_usuario=usuario.id_usuario,
        telefono=payload.telefono,
        fecha_nacimiento=payload.fecha_nacimiento,
    )
    session.add(paciente)

    await auditoria_service.registrar(
        session,
        accion=Accion.ALTA_PACIENTE_RECEPCION,
        id_usuario=usuario.id_usuario,
        entidad="paciente",
        entidad_id=paciente.id_paciente,
        datos_despues={
            "dni": usuario.dni,
            "email": usuario.email,
            "origen": "RECEPCION",
            # La contraseña temporal nunca se audita.
        },
        request=request,
        commit=False,
    )
    await session.commit()
    return _salida(paciente, usuario)


def _escapar_like(texto: str) -> str:
    """Escapa comodines % y _ para búsquedas ILIKE seguras."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _consulta_base() -> Select[Paciente, Usuario]:
    return (
        select(Paciente, Usuario)
        .join(Usuario, Paciente.id_usuario == Usuario.id_usuario)
        .where(Usuario.rol == RolUsuario.PACIENTE)
    )


async def listar(
    session: AsyncSession, *, q: str | None, page: int, page_size: int
) -> Pagina[PacienteOut]:
    consulta = _consulta_base()
    if q and q.strip():
        patron = f"%{_escapar_like(q.strip())}%"
        consulta = consulta.where(
            or_(
                Usuario.dni.ilike(patron),
                Usuario.nombre.ilike(patron),
                Usuario.apellido.ilike(patron),
                Usuario.email.ilike(patron),
            )
        )

    total = await session.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    filas = (
        await session.execute(
            consulta.order_by(Usuario.apellido, Usuario.nombre, Usuario.dni)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    return Pagina.de(
        [_salida(fila[0], fila[1]) for fila in filas],
        page=page,
        page_size=page_size,
        total=total,
    )


async def obtener(session: AsyncSession, id_paciente: UUID) -> PacienteOut:
    fila = (
        await session.execute(_consulta_base().where(Paciente.id_paciente == id_paciente))
    ).first()
    if fila is None:
        raise ApiError(404, "PACIENTE_NO_ENCONTRADO", "No encontrado", "El paciente no existe.")
    return _salida(fila[0], fila[1])


async def actualizar(
    session: AsyncSession, *, id_paciente: UUID, payload: PacienteUpdate, request: Request
) -> PacienteOut:
    fila = (
        await session.execute(_consulta_base().where(Paciente.id_paciente == id_paciente))
    ).first()
    if fila is None:
        raise ApiError(404, "PACIENTE_NO_ENCONTRADO", "No encontrado", "El paciente no existe.")
    paciente, usuario = fila[0], fila[1]

    cambios = payload.model_dump(exclude_unset=True)
    antes: dict[str, object] = {}
    despues: dict[str, object] = {}

    if "email" in cambios and cambios["email"] != usuario.email:
        await _verificar_unicidad(
            session, dni=usuario.dni, email=str(cambios["email"]), id_usuario=usuario.id_usuario
        )
        antes["email"] = usuario.email
        usuario.email = str(cambios["email"])
        despues["email"] = usuario.email

    for campo in ("nombre", "apellido"):
        if campo in cambios and cambios[campo] != getattr(usuario, campo):
            antes[campo] = getattr(usuario, campo)
            setattr(usuario, campo, cambios[campo])
            despues[campo] = getattr(usuario, campo)

    for campo in ("telefono", "fecha_nacimiento"):
        if campo in cambios and cambios[campo] != getattr(paciente, campo):
            antes[campo] = getattr(paciente, campo)
            setattr(paciente, campo, cambios[campo])
            despues[campo] = getattr(paciente, campo)

    if not despues:
        return _salida(paciente, usuario)

    await auditoria_service.registrar(
        session,
        accion=Accion.MODIFICACION_PACIENTE,
        id_usuario=usuario.id_usuario,
        entidad="paciente",
        entidad_id=paciente.id_paciente,
        datos_antes=antes,
        datos_despues=despues,
        request=request,
        commit=False,
    )
    await session.commit()
    return _salida(paciente, usuario)
