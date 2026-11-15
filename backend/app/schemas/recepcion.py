from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TurnoEnEsperaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_turno: UUID
    id_paciente: UUID
    id_medico: UUID
    paciente_nombre: str
    paciente_apellido: str
    paciente_dni: str
    medico_nombre: str
    medico_apellido: str
    especialidad_nombre: str
    fecha_hora: datetime
    fecha_hora_llegada: datetime
    duracion_minutos: int
    en_tolerancia: bool
    orden_atencion: int


class CierreJornadaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_ausentes: int
    turnos_afectados: list[UUID]
