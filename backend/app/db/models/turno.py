from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import EstadoTurno, MotivoCancelacion


class Turno(Base):
    __tablename__ = "turno"
    __table_args__ = (
        CheckConstraint("duracion_minutos > 0", name="duracion_positiva"),
        Index("ix_turno_medico_fecha", "id_medico", "fecha_hora"),
        Index("ix_turno_paciente_fecha", "id_paciente", "fecha_hora"),
        Index("ix_turno_estado_fecha", "estado", "fecha_hora"),
        Index("ix_turno_fecha", "fecha_hora"),
    )

    id_turno: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    id_paciente: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("paciente.id_paciente", name="fk_turno_paciente"),
        nullable=False,
    )
    id_medico: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("medico.id_medico", name="fk_turno_medico"),
        nullable=False,
    )
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duracion_minutos: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[EstadoTurno] = mapped_column(
        Enum(EstadoTurno, name="estado_turno", native_enum=True),
        nullable=False,
        server_default=text("'RESERVADO'::estado_turno"),
    )
    fecha_hora_llegada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_hora_cancelacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    id_usuario_creador: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id_usuario", name="fk_turno_usuario_creador"),
        nullable=False,
    )
    motivo_cancelacion: Mapped[MotivoCancelacion | None] = mapped_column(
        Enum(MotivoCancelacion, name="motivo_cancelacion", native_enum=True)
    )
    detalle_cancelacion: Mapped[str | None] = mapped_column(Text)
    id_usuario_cancelacion: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id_usuario", name="fk_turno_usuario_cancelacion"),
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
