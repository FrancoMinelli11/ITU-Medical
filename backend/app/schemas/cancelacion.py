from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.models.enums import EstadoSolicitudCancelacion, MotivoCancelacion


class CancelacionPacienteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str | None = Field(None, max_length=500)


class CancelacionRecepcionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: MotivoCancelacion
    detalle: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def validar_detalle_si_es_otro(self) -> CancelacionRecepcionRequest:
        if self.motivo == MotivoCancelacion.OTRO and not (self.detalle and self.detalle.strip()):
            raise ValueError("El detalle es obligatorio cuando el motivo de cancelación es OTRO.")
        return self


class SolicitudCancelacionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(..., min_length=5, max_length=500)


class SolicitudCancelacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_solicitud: UUID
    id_turno: UUID
    id_paciente: UUID
    motivo: str
    estado: EstadoSolicitudCancelacion
    id_usuario_resolucion: UUID | None = None
    fecha_resolucion: datetime | None = None
    detalle_resolucion: str | None = None
    fecha_creacion: datetime
    paciente_nombre: str | None = None
    paciente_apellido: str | None = None
    paciente_dni: str | None = None
    turno_fecha_hora: datetime | None = None
    medico_nombre: str | None = None
    medico_apellido: str | None = None
    especialidad_nombre: str | None = None


class ResolucionSolicitudRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aprobada: bool
    detalle: str | None = Field(None, max_length=500)
