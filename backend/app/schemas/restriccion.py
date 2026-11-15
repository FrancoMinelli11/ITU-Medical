from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RestriccionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_paciente: UUID
    motivo: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Motivo de la restricción (por ej. ausencias reiteradas sin aviso).",
    )
    dias_vigencia: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Cantidad de días de vigencia de la restricción (30 por defecto, RN-20).",
    )


class RestriccionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_restriccion: UUID
    id_usuario: UUID
    id_paciente: UUID | None = None
    motivo: str
    fecha_inicio: datetime
    fecha_fin: datetime
    activa: bool
    vigente: bool
    id_usuario_creador: UUID
    fecha_creacion: datetime
    paciente_nombre: str | None = None
    paciente_apellido: str | None = None
    paciente_dni: str | None = None


class RestriccionEstadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_paciente: UUID
    id_usuario: UUID
    es_usuario_rojo: bool
    restriccion_activa: RestriccionOut | None = None
