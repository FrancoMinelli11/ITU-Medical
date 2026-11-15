from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import EstadoTurno, MotivoCancelacion


class ReservaTurnoWebRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_medico: UUID
    fecha_hora: datetime = Field(
        ...,
        description="Fecha y hora de inicio del turno en formato ISO-8601 (con o sin timezone).",
    )


class ReservaTurnoRecepcionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_paciente: UUID | None = None
    dni_paciente: str | None = Field(None, min_length=7, max_length=8)
    id_medico: UUID
    fecha_hora: datetime = Field(
        ...,
        description="Fecha y hora de inicio del turno en formato ISO-8601.",
    )


class TurnoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_turno: UUID
    id_paciente: UUID
    id_medico: UUID
    fecha_hora: datetime
    duracion_minutos: int
    estado: EstadoTurno
    fecha_hora_llegada: datetime | None = None
    fecha_hora_cancelacion: datetime | None = None
    motivo_cancelacion: MotivoCancelacion | None = None
    detalle_cancelacion: str | None = None
    medico_nombre: str | None = None
    medico_apellido: str | None = None
    especialidad_nombre: str | None = None
    paciente_nombre: str | None = None
    paciente_apellido: str | None = None
    paciente_dni: str | None = None
    fecha_creacion: datetime


class TurnosListResponse(BaseModel):
    items: list[TurnoResponse]
    total: int
    pagina: int
    tamano_pagina: int
