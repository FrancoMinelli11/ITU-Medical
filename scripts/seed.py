"""Seed idempotente para desarrollo, demos y tests (S-14).

Uso:
    python scripts/seed.py

Cubre el escenario S-14: 1 administrador, 2 recepcionistas, 3 médicos en 3
especialidades distintas y 2 pacientes con email verificado. Correrlo dos veces
no duplica filas.

Incluye una normalización de los datos del seed anterior (un correo por rol y
"Clínica Médica" -> "Clínica") para que una base ya sembrada converja al mismo
estado que una base nueva, sin violar los UNIQUE de `dni`, `email` ni
`matricula`.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path

from sqlalchemy import or_, select, update

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.models import (  # noqa: E402
    Especialidad,
    HorarioMedico,
    Medico,
    Paciente,
    RolUsuario,
    Usuario,
)
from app.db.session import SessionLocal, engine  # noqa: E402

PASSWORD_RECEPCION = "Recepcion123!"
PASSWORD_MEDICO = "Medico12345!"
PASSWORD_PACIENTE = "Paciente123!"

ESPECIALIDADES = ["Clínica", "Cardiología", "Pediatría"]

# Cada médico queda en una especialidad distinta.
ASIGNACIONES_MEDICOS: list[tuple[str, str, str]] = [
    ("medico1@turnos.local", "Clínica", "MP-1001"),
    ("medico2@turnos.local", "Cardiología", "MP-1002"),
    ("medico3@turnos.local", "Pediatría", "MP-1003"),
]

NACIMIENTOS = {
    "paciente1@turnos.local": date(1990, 1, 1),
    "paciente2@turnos.local": date(1985, 7, 20),
}

# Correos del seed anterior (un único usuario por rol).
CORREOS_LEGACY = {
    "recepcion@turnos.local": "recepcion1@turnos.local",
    "medico@turnos.local": "medico1@turnos.local",
    "paciente@turnos.local": "paciente1@turnos.local",
}
ESPECIALIDAD_LEGACY = ("Clínica Médica", "Clínica")


@dataclass(frozen=True)
class DatosUsuario:
    dni: str
    email: str
    password: str
    rol: RolUsuario
    nombre: str
    apellido: str
    descripcion: str


@dataclass(frozen=True)
class Credencial:
    descripcion: str
    email: str
    password: str


# El administrador toma sus datos de SEED_ADMIN_* en .env (ver main()).
USUARIOS: list[DatosUsuario] = [
    DatosUsuario(
        "10000000",
        "admin@turnos.local",
        "Admin12345!",
        RolUsuario.ADMINISTRADOR,
        "Admin",
        "Sistema",
        "Administrador",
    ),
    DatosUsuario(
        "10000001",
        "recepcion1@turnos.local",
        PASSWORD_RECEPCION,
        RolUsuario.RECEPCIONISTA,
        "Lucía",
        "Fernández",
        "Recepción 1",
    ),
    DatosUsuario(
        "10000003",
        "recepcion2@turnos.local",
        PASSWORD_RECEPCION,
        RolUsuario.RECEPCIONISTA,
        "Marcos",
        "Pereyra",
        "Recepción 2",
    ),
    DatosUsuario(
        "10000002",
        "medico1@turnos.local",
        PASSWORD_MEDICO,
        RolUsuario.MEDICO,
        "Roberto",
        "Martínez",
        "Médico 1 (Clínica)",
    ),
    DatosUsuario(
        "10000004",
        "medico2@turnos.local",
        PASSWORD_MEDICO,
        RolUsuario.MEDICO,
        "Silvina",
        "Rossi",
        "Médico 2 (Cardiología)",
    ),
    DatosUsuario(
        "10000005",
        "medico3@turnos.local",
        PASSWORD_MEDICO,
        RolUsuario.MEDICO,
        "Diego",
        "Álvarez",
        "Médico 3 (Pediatría)",
    ),
    DatosUsuario(
        "20000000",
        "paciente1@turnos.local",
        PASSWORD_PACIENTE,
        RolUsuario.PACIENTE,
        "Camila",
        "Duarte",
        "Paciente 1",
    ),
    DatosUsuario(
        "20000001",
        "paciente2@turnos.local",
        PASSWORD_PACIENTE,
        RolUsuario.PACIENTE,
        "Julián",
        "Sosa",
        "Paciente 2",
    ),
]


def validar_password(password: str) -> None:
    """Política RN-28: al menos 10 caracteres, una letra y un dígito."""
    if (
        len(password) < 10
        or not any(caracter.isalpha() for caracter in password)
        or not any(caracter.isdigit() for caracter in password)
    ):
        raise ValueError(f"Contraseña de seed fuera de política (RN-28): {password!r}")


async def normalizar_datos_legacy(session) -> list[str]:
    """Converge una base sembrada con la versión anterior al esquema actual."""
    cambios: list[str] = []

    for viejo, nuevo in CORREOS_LEGACY.items():
        ya_existe = await session.scalar(select(Usuario.id_usuario).where(Usuario.email == nuevo))
        if ya_existe is not None:
            continue
        resultado = await session.execute(
            update(Usuario)
            .where(Usuario.email == viejo)
            .values(email=nuevo)
            .returning(Usuario.id_usuario)
        )
        if resultado.scalar_one_or_none() is not None:
            cambios.append(f"{viejo} -> {nuevo}")

    viejo_esp, nuevo_esp = ESPECIALIDAD_LEGACY
    ya_existe = await session.scalar(
        select(Especialidad.id_especialidad).where(Especialidad.nombre == nuevo_esp)
    )
    if ya_existe is None:
        resultado = await session.execute(
            update(Especialidad)
            .where(Especialidad.nombre == viejo_esp)
            .values(nombre=nuevo_esp)
            .returning(Especialidad.id_especialidad)
        )
        if resultado.scalar_one_or_none() is not None:
            cambios.append(f"especialidad {viejo_esp} -> {nuevo_esp}")

    return cambios


async def get_or_create_usuario(
    session,
    *,
    dni: str,
    email: str,
    password: str,
    rol: RolUsuario,
    nombre: str,
    apellido: str,
    email_verificado: bool = True,
    debe_cambiar_password: bool = False,
) -> Usuario:
    validar_password(password)
    result = await session.execute(
        select(Usuario).where(or_(Usuario.email == email, Usuario.dni == dni))
    )
    usuario = result.scalar_one_or_none()
    if usuario is not None:
        return usuario

    usuario = Usuario(
        dni=dni,
        email=email,
        password_hash=hash_password(password),
        rol=rol,
        nombre=nombre,
        apellido=apellido,
        email_verificado=email_verificado,
        debe_cambiar_password=debe_cambiar_password,
    )
    session.add(usuario)
    await session.flush()
    return usuario


async def get_or_create_especialidad(session, nombre: str) -> Especialidad:
    result = await session.execute(select(Especialidad).where(Especialidad.nombre == nombre))
    especialidad = result.scalar_one_or_none()
    if especialidad is not None:
        return especialidad
    especialidad = Especialidad(nombre=nombre)
    session.add(especialidad)
    await session.flush()
    return especialidad


async def get_or_create_medico(
    session, *, usuario: Usuario, especialidad: Especialidad, matricula: str
) -> Medico:
    medico = await session.scalar(select(Medico).where(Medico.id_usuario == usuario.id_usuario))
    if medico is None:
        medico = Medico(
            id_usuario=usuario.id_usuario,
            id_especialidad=especialidad.id_especialidad,
            matricula=matricula,
        )
        session.add(medico)
        await session.flush()
        return medico

    if medico.id_especialidad != especialidad.id_especialidad or medico.matricula != matricula:
        medico.id_especialidad = especialidad.id_especialidad
        medico.matricula = matricula
        await session.flush()
    return medico


async def get_or_create_paciente(session, *, usuario: Usuario, fecha_nacimiento: date) -> Paciente:
    paciente = await session.scalar(
        select(Paciente).where(Paciente.id_usuario == usuario.id_usuario)
    )
    if paciente is None:
        paciente = Paciente(id_usuario=usuario.id_usuario, fecha_nacimiento=fecha_nacimiento)
        session.add(paciente)
        await session.flush()
        return paciente

    if paciente.fecha_nacimiento != fecha_nacimiento:
        paciente.fecha_nacimiento = fecha_nacimiento
        await session.flush()
    return paciente


async def asegurar_horarios_seed(session, medico: Medico) -> None:
    """Crea horarios lunes-viernes 9-13 hs, 30 min, si no existen ya."""
    from sqlalchemy import select as sql_select

    existente = await session.scalar(
        sql_select(HorarioMedico).where(HorarioMedico.id_medico == medico.id_medico).limit(1)
    )
    if existente is not None:
        return  # ya tiene horarios: idempotente

    for dia in range(0, 5):  # 0=Lunes … 4=Viernes
        horario = HorarioMedico(
            id_medico=medico.id_medico,
            dia_semana=dia,
            hora_inicio=time(9, 0),
            hora_fin=time(13, 0),
            duracion_minutos=30,
            activo=True,
        )
        session.add(horario)
    await session.flush()


def datos_con_admin_configurable(datos: DatosUsuario, settings) -> DatosUsuario:
    """El administrador se configura por SEED_ADMIN_* (.env)."""
    if datos.rol is not RolUsuario.ADMINISTRADOR:
        return datos
    return DatosUsuario(
        dni=settings.seed_admin_dni,
        email=settings.seed_admin_email,
        password=settings.seed_admin_password,
        rol=datos.rol,
        nombre=datos.nombre,
        apellido=datos.apellido,
        descripcion=datos.descripcion,
    )


async def main() -> None:
    settings = get_settings()
    credenciales: list[Credencial] = []

    async with SessionLocal() as session:
        cambios = await normalizar_datos_legacy(session)

        especialidades = {
            nombre: await get_or_create_especialidad(session, nombre) for nombre in ESPECIALIDADES
        }

        usuarios: dict[str, Usuario] = {}
        for datos in USUARIOS:
            datos = datos_con_admin_configurable(datos, settings)
            usuario = await get_or_create_usuario(
                session,
                dni=datos.dni,
                email=datos.email,
                password=datos.password,
                rol=datos.rol,
                nombre=datos.nombre,
                apellido=datos.apellido,
            )
            usuarios[usuario.email] = usuario
            credenciales.append(
                Credencial(
                    descripcion=datos.descripcion,
                    email=usuario.email,
                    password=datos.password,
                )
            )

        for email, nombre_especialidad, matricula in ASIGNACIONES_MEDICOS:
            await get_or_create_medico(
                session,
                usuario=usuarios[email],
                especialidad=especialidades[nombre_especialidad],
                matricula=matricula,
            )

        for email, nombre_especialidad, matricula in ASIGNACIONES_MEDICOS:
            medico_obj = await session.scalar(
                select(Medico).where(Medico.id_usuario == usuarios[email].id_usuario)
            )
            if medico_obj:
                await asegurar_horarios_seed(session, medico_obj)

        for email, nacimiento in NACIMIENTOS.items():
            await get_or_create_paciente(
                session,
                usuario=usuarios[email],
                fecha_nacimiento=nacimiento,
            )

        await session.commit()

    await engine.dispose()

    if cambios:
        print("Normalización de datos del seed anterior:")
        for cambio in cambios:
            print(f"  - {cambio}")
        print()

    print("Seed completado (S-14). Todos los correos quedan verificados.")
    print("Horarios: lunes-viernes 09:00-13:00 cada 30 min para los 3 médicos.")
    print("Credenciales de desarrollo:")
    for credencial in credenciales:
        print(f"  {credencial.descripcion:<18} {credencial.email:<26} {credencial.password}")
    print()
    print("  Especialidades: " + ", ".join(ESPECIALIDADES))


if __name__ == "__main__":
    asyncio.run(main())
