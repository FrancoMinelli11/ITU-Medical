from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EspecialidadCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    nombre: str = Field(..., min_length=2, max_length=120)
    descripcion: str | None = Field(None, max_length=500)


class EspecialidadUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    nombre: str | None = Field(None, min_length=2, max_length=120)
    descripcion: str | None = Field(None, max_length=500)
    activa: bool | None = None


class EspecialidadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_especialidad: UUID
    nombre: str
    descripcion: str | None
    activa: bool
    fecha_creacion: datetime
