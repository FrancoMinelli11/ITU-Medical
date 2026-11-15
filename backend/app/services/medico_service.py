"""Gestión de profesionales médicos (RF-18)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.exceptions import ApiError
from app.core.security import hash_password
from app.core.timezone import now_utc
from app.db.models.enums import EstadoTurno, RolUsuario
from app.db.models.especialidad import Especialidad
from app.db.models.medico import Medico
from app.db.models.turno import Turno
from app.db.models.usuario import Usuario
from app.schemas.common import Pagina
from app.schemas.medico import MedicoCreate, MedicoOut, MedicoUpdate, TurnoAfectadoOut
from app.services import auditoria_service
from app.services.auditoria_service import Accion

MEDICO_NO_ENCONTRADO = (
    404,
    "MEDICO_NO_ENCONTRADO",
    "No encontrado",
    "El médico no existe.",
)
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
MATRICULA_DUPLICADA = (
    409,
    "MATRICULA_DUPLICADA",
    "Matrícula duplicada",
    "Ya existe un médico registrado con esa matrícula.",
)
ESPECIALIDAD_INEXISTENTE = (
    400,
    "ESPECIALIDAD_INEXISTENTE",
    "Especialidad inválida",
    "La especialidad indicada no existe o no está activa.",
)


def _salida(medico: Medico, usuario: Usuario, especialidad: Especialidad) -> MedicoOut:
    return MedicoOut(
        id_medico=medico.id_medico,
        id_usuario=usuario.id_usuario,
        dni=usuario.dni,
        email=usuario.email,
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        id_especialidad=especialidad.id_especialidad,
        especialidad_nombre=especialidad.nombre,
        matricula=medico.matricula,
        activo=medico.activo and usuario.habilitado,
        fecha_creacion=medico.fecha_creacion,
    )


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def listar(
    session: AsyncSession,
    *,
    q: str | None = None,
    id_especialidad: UUID | None = None,
    solo_activos: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> Pagina[MedicoOut]:
    consulta = (
        select(Medico, Usuario, Especialidad)
        .join(Usuario, Medico.id_usuario == Usuario.id_usuario)
        .join(Especialidad, Medico.id_especialidad == Especialidad.id_especialidad)
    )

    if solo_activos:
        consulta = consulta.where(Medico.activo.is_(True), Usuario.habilitado.is_(True))

    if id_especialidad is not None:
        consulta = consulta.where(Medico.id_especialidad == id_especialidad)

    if q and q.strip():
        patron = f"%{_escapar_like(q.strip())}%"
        consulta = consulta.where(
            or_(
                Usuario.dni.ilike(patron),
                Usuario.nombre.ilike(patron),
                Usuario.apellido.ilike(patron),
                Usuario.email.ilike(patron),
                Medico.matricula.ilike(patron),
            )
        )

    total = await session.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    filas = (
        await session.execute(
            consulta.order_by(Usuario.apellido, Usuario.nombre)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    items = [_salida(fila[0], fila[1], fila[2]) for fila in filas]
    return Pagina.de(items, page=page, page_size=page_size, total=total)


async def obtener(session: AsyncSession, id_medico: UUID) -> MedicoOut:
    fila = (
        await session.execute(
            select(Medico, Usuario, Especialidad)
            .join(Usuario, Medico.id_usuario == Usuario.id_usuario)
            .join(Especialidad, Medico.id_especialidad == Especialidad.id_especialidad)
            .where(Medico.id_medico == id_medico)
        )
    ).first()

    if fila is None:
        raise ApiError(*MEDICO_NO_ENCONTRADO)

    return _salida(fila[0], fila[1], fila[2])


async def crear(session: AsyncSession, *, payload: MedicoCreate, request: Request) -> MedicoOut:
    # 1. Unicidad de DNI y Email
    if await session.scalar(select(Usuario.id_usuario).where(Usuario.dni == payload.dni)):
        raise ApiError(*DNI_DUPLICADO)

    if await session.scalar(select(Usuario.id_usuario).where(Usuario.email == payload.email)):
        raise ApiError(*EMAIL_DUPLICADO)

    # 2. Unicidad de Matrícula
    if payload.matricula:
        query_mat = select(Medico.id_medico).where(Medico.matricula == payload.matricula)
        if await session.scalar(query_mat) is not None:
            raise ApiError(*MATRICULA_DUPLICADA)

    # 3. Especialidad existe y está activa
    especialidad = await session.get(Especialidad, payload.id_especialidad)
    if especialidad is None or not especialidad.activa:
        raise ApiError(*ESPECIALIDAD_INEXISTENTE)

    # Si no se pasó password, se usa el DNI como temporal y debe cambiarla
    debe_cambiar = payload.password is None
    password_plana = payload.password or payload.dni

    usuario = Usuario(
        dni=payload.dni,
        email=payload.email,
        password_hash=hash_password(password_plana),
        rol=RolUsuario.MEDICO,
        nombre=payload.nombre,
        apellido=payload.apellido,
        email_verificado=True,
        debe_cambiar_password=debe_cambiar,
        habilitado=True,
    )
    session.add(usuario)
    await session.flush()

    medico = Medico(
        id_usuario=usuario.id_usuario,
        id_especialidad=especialidad.id_especialidad,
        matricula=payload.matricula,
        activo=True,
    )
    session.add(medico)
    await session.flush()

    await auditoria_service.registrar(
        session,
        accion=Accion.ALTA_MEDICO,
        id_usuario=usuario.id_usuario,
        entidad="medico",
        entidad_id=medico.id_medico,
        datos_despues={
            "dni": usuario.dni,
            "email": usuario.email,
            "matricula": medico.matricula,
            "id_especialidad": str(especialidad.id_especialidad),
        },
        request=request,
        commit=False,
    )
    await session.commit()
    return _salida(medico, usuario, especialidad)


async def actualizar(
    session: AsyncSession, *, id_medico: UUID, payload: MedicoUpdate, request: Request
) -> MedicoOut:
    fila = (
        await session.execute(
            select(Medico, Usuario, Especialidad)
            .join(Usuario, Medico.id_usuario == Usuario.id_usuario)
            .join(Especialidad, Medico.id_especialidad == Especialidad.id_especialidad)
            .where(Medico.id_medico == id_medico)
        )
    ).first()

    if fila is None:
        raise ApiError(*MEDICO_NO_ENCONTRADO)

    medico, usuario, especialidad = fila[0], fila[1], fila[2]
    cambios = payload.model_dump(exclude_unset=True)
    antes: dict[str, object] = {}
    despues: dict[str, object] = {}

    if "matricula" in cambios:
        nueva_matricula = str(cambios["matricula"]).strip() if cambios["matricula"] else None
        if nueva_matricula != medico.matricula:
            if nueva_matricula is not None:
                conflicto = await session.scalar(
                    select(Medico.id_medico).where(
                        Medico.matricula == nueva_matricula,
                        Medico.id_medico != id_medico,
                    )
                )
                if conflicto is not None:
                    raise ApiError(*MATRICULA_DUPLICADA)
            antes["matricula"] = medico.matricula
            medico.matricula = nueva_matricula
            despues["matricula"] = nueva_matricula

    if "id_especialidad" in cambios and cambios["id_especialidad"] != especialidad.id_especialidad:
        nueva_esp = await session.get(Especialidad, cambios["id_especialidad"])
        if nueva_esp is None or not nueva_esp.activa:
            raise ApiError(*ESPECIALIDAD_INEXISTENTE)
        antes["id_especialidad"] = str(especialidad.id_especialidad)
        medico.id_especialidad = nueva_esp.id_especialidad
        especialidad = nueva_esp
        despues["id_especialidad"] = str(nueva_esp.id_especialidad)

    for campo in ("nombre", "apellido"):
        if campo in cambios and cambios[campo] != getattr(usuario, campo):
            antes[campo] = getattr(usuario, campo)
            setattr(usuario, campo, cambios[campo])
            despues[campo] = getattr(usuario, campo)

    if "activo" in cambios and cambios["activo"] is not None and cambios["activo"] != medico.activo:
        nuevo_activo = bool(cambios["activo"])
        # RF-18: Si se quiere deshabilitar, no debe tener turnos futuros activos
        if not nuevo_activo:
            ahora = now_utc()
            turnos_afectados = (
                await session.scalars(
                    select(Turno)
                    .where(
                        Turno.id_medico == id_medico,
                        Turno.estado.in_([EstadoTurno.RESERVADO, EstadoTurno.EN_ESPERA]),
                        Turno.fecha_hora >= ahora,
                    )
                    .order_by(Turno.fecha_hora)
                )
            ).all()

            if turnos_afectados:
                lista_turnos = [
                    TurnoAfectadoOut(
                        id_turno=t.id_turno,
                        fecha_hora=t.fecha_hora,
                        duracion_minutos=t.duracion_minutos,
                        id_paciente=t.id_paciente,
                    ).model_dump(mode="json")
                    for t in turnos_afectados
                ]
                raise ApiError(
                    409,
                    "MEDICO_CON_TURNOS_FUTUROS",
                    "Médico con turnos futuros",
                    "No se puede deshabilitar al profesional porque tiene turnos pendientes.",
                    errors=lista_turnos,
                )

        antes["activo"] = medico.activo
        medico.activo = nuevo_activo
        usuario.habilitado = nuevo_activo
        despues["activo"] = nuevo_activo

    if not despues:
        return _salida(medico, usuario, especialidad)

    await auditoria_service.registrar(
        session,
        accion=Accion.MODIFICACION_MEDICO,
        id_usuario=usuario.id_usuario,
        entidad="medico",
        entidad_id=medico.id_medico,
        datos_antes=antes,
        datos_despues=despues,
        request=request,
        commit=False,
    )
    await session.commit()
    return _salida(medico, usuario, especialidad)
