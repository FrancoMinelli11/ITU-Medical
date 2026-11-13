from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import EstadoSolicitudCancelacion


class SolicitudCancelacion(Base):
    __tablename__ = "solicitud_cancelacion"
    __table_args__ = (
        Index("ix_solicitud_estado", "estado"),
        Index("ix_solicitud_turno", "id_turno"),
    )

    id_solicitud: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    id_turno: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("turno.id_turno", name="fk_solicitud_turno"),
        nullable=False,
    )
    id_paciente: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("paciente.id_paciente", name="fk_solicitud_paciente"),
        nullable=False,
    )
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[EstadoSolicitudCancelacion] = mapped_column(
        Enum(
            EstadoSolicitudCancelacion,
            name="estado_solicitud_cancelacion",
            native_enum=True,
        ),
        nullable=False,
        server_default=text("'PENDIENTE'::estado_solicitud_cancelacion"),
    )
    id_usuario_resolucion: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id_usuario", name="fk_solicitud_usuario_resolucion"),
    )
    fecha_resolucion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    detalle_resolucion: Mapped[str | None] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
