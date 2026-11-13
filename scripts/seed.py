"""Seed idempotente para desarrollo y demos.

Uso:
    python scripts/seed.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import or_, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.models import (  # noqa: E402
    Especialidad,
    Medico,
    Paciente,
    RolUsuario,
    Usuario,
)
from app.db.session import SessionLocal, engine  # noqa: E402


async def get_or_create_usuario(
    session,
    *,
    dni: str,
    email: str,
    password: str,
    rol: RolUsuario,
    nombre: str,
    apellido: str,
    email_verificado: bool,
    debe_cambiar_password: bool = False,
) -> Usuario:
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


async def main() -> None:
    settings = get_settings()
    async with SessionLocal() as session:
        clinica = await get_or_create_especialidad(session, "Clínica Médica")
        await get_or_create_especialidad(session, "Pediatría")
        await get_or_create_especialidad(session, "Cardiología")

        admin = await get_or_create_usuario(
            session,
            dni=settings.seed_admin_dni,
            email=settings.seed_admin_email,
            password=settings.seed_admin_password,
            rol=RolUsuario.ADMINISTRADOR,
            nombre="Admin",
            apellido="Sistema",
            email_verificado=True,
        )
        await get_or_create_usuario(
            session,
            dni="10000001",
            email="recepcion@turnos.local",
            password="Recepcion123!",
            rol=RolUsuario.RECEPCIONISTA,
            nombre="Lucía",
            apellido="Fernández",
            email_verificado=True,
        )
        medico_user = await get_or_create_usuario(
            session,
            dni="10000002",
            email="medico@turnos.local",
            password="Medico12345!",
            rol=RolUsuario.MEDICO,
            nombre="Roberto",
            apellido="Martínez",
            email_verificado=True,
        )
        paciente_user = await get_or_create_usuario(
            session,
            dni="20000000",
            email="paciente@turnos.local",
            password="Paciente123!",
            rol=RolUsuario.PACIENTE,
            nombre="Camila",
            apellido="Duarte",
            email_verificado=True,
        )

        medico_result = await session.execute(
            select(Medico).where(Medico.id_usuario == medico_user.id_usuario)
        )
        if medico_result.scalar_one_or_none() is None:
            session.add(
                Medico(
                    id_usuario=medico_user.id_usuario,
                    id_especialidad=clinica.id_especialidad,
                    matricula="MP-1001",
                )
            )

        paciente_result = await session.execute(
            select(Paciente).where(Paciente.id_usuario == paciente_user.id_usuario)
        )
        if paciente_result.scalar_one_or_none() is None:
            session.add(
                Paciente(
                    id_usuario=paciente_user.id_usuario,
                    fecha_nacimiento=date(1990, 1, 1),
                )
            )

        await session.commit()
        print("Seed completado.")
        print(f"Admin:    {admin.email} / {settings.seed_admin_password}")
        print("Recepción: recepcion@turnos.local / Recepcion123!")
        print("Médico:   medico@turnos.local / Medico12345!")
        print("Paciente: paciente@turnos.local / Paciente123!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
