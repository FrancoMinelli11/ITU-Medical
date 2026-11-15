from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotaSeguimientoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_paciente: UUID
    id_turno: UUID | None = None
    contenido: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Anotación breve sobre avances, mejoras o seguimiento del paciente.",
    )


class NotaSeguimientoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contenido: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Contenido modificado de la anotación médica.",
    )


class NotaSeguimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_nota: UUID
    id_medico: UUID
    id_paciente: UUID
    id_turno: UUID | None = None
    contenido: str
    fecha_creacion: datetime
    fecha_modificacion: datetime
    medico_nombre: str | None = None
    medico_apellido: str | None = None
    especialidad_nombre: str | None = None
