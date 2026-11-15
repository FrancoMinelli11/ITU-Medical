from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth import DNI_PATTERN, EmailNormalizado, PasswordFuerte


class MedicoCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    dni: str = Field(..., min_length=7, max_length=8, pattern=DNI_PATTERN)
    email: EmailNormalizado
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    password: PasswordFuerte | None = None
    id_especialidad: UUID
    matricula: str | None = Field(None, max_length=50)


class MedicoUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    nombre: str | None = Field(None, min_length=1, max_length=100)
    apellido: str | None = Field(None, min_length=1, max_length=100)
    id_especialidad: UUID | None = None
    matricula: str | None = Field(None, max_length=50)
    activo: bool | None = None


class TurnoAfectadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_turno: UUID
    fecha_hora: datetime
    duracion_minutos: int
    id_paciente: UUID


class MedicoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_medico: UUID
    id_usuario: UUID
    dni: str
    email: str
    nombre: str
    apellido: str
    id_especialidad: UUID
    especialidad_nombre: str
    matricula: str | None
    activo: bool
    fecha_creacion: datetime
