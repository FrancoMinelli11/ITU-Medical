from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import EstadoTurno


class HorarioItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dia_semana: int = Field(..., ge=0, le=6, description="0=Lunes, 6=Domingo")
    hora_inicio: time
    hora_fin: time
    duracion_minutos: int = Field(30, gt=0, le=240)
    activo: bool = True


class HorariosSetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    horarios: list[HorarioItem]


class HorarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_horario: UUID
    id_medico: UUID
    dia_semana: int
    hora_inicio: time
    hora_fin: time
    duracion_minutos: int
    activo: bool


class BloqueoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    inicio: datetime
    fin: datetime
    motivo: str = Field(..., min_length=1, max_length=255)


class BloqueoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_bloqueo: UUID
    id_medico: UUID
    inicio: datetime
    fin: datetime
    motivo: str
    id_usuario_creador: UUID
    fecha_creacion: datetime


class SlotDisponibilidad(BaseModel):
    fecha_hora: datetime
    duracion_minutos: int


class DisponibilidadOut(BaseModel):
    id_medico: UUID
    fecha_desde: date
    fecha_hasta: date
    slots: list[SlotDisponibilidad]


class AgendaTurnoOut(BaseModel):
    id_turno: UUID
    fecha_hora: datetime
    duracion_minutos: int
    estado: EstadoTurno
    id_paciente: UUID
    paciente_nombre: str
    paciente_apellido: str
    paciente_dni: str


class AgendaOut(BaseModel):
    id_medico: UUID
    turnos: list[AgendaTurnoOut]
    bloqueos: list[BloqueoOut]
