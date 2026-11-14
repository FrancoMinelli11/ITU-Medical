"""Contratos de `/pacientes` (RF-01, RF-02, CU-02)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.auth import DNI_PATTERN, EmailNormalizado


class PacienteOut(BaseModel):
    id_paciente: UUID
    id_usuario: UUID
    dni: str
    email: str
    nombre: str
    apellido: str
    telefono: str | None = None
    fecha_nacimiento: date | None = None
    email_verificado: bool
    habilitado: bool
    debe_cambiar_password: bool
    fecha_creacion: datetime


class PacienteCreate(BaseModel):
    """Alta desde recepción (RF-02).

    No lleva contraseña: la inicial es el DNI literal y se exige cambiarla en el
    primer ingreso (RN-29). El correo se considera verificado al crearse.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    dni: str = Field(min_length=7, max_length=8, pattern=DNI_PATTERN)
    email: EmailNormalizado
    nombre: str = Field(min_length=1, max_length=80)
    apellido: str = Field(min_length=1, max_length=80)
    telefono: str | None = Field(default=None, max_length=30)
    fecha_nacimiento: date | None = None

    @model_validator(mode="after")
    def _sin_vacios(self) -> PacienteCreate:
        if not self.nombre.strip() or not self.apellido.strip():
            raise ValueError("Nombre y apellido no pueden quedar vacíos.")
        return self


class PacienteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailNormalizado | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    apellido: str | None = Field(default=None, min_length=1, max_length=80)
    telefono: str | None = Field(default=None, max_length=30)
    fecha_nacimiento: date | None = None

    @model_validator(mode="after")
    def _al_menos_un_campo(self) -> PacienteUpdate:
        if not self.model_dump(exclude_unset=True):
            raise ValueError("Indicá al menos un campo para modificar.")
        return self
