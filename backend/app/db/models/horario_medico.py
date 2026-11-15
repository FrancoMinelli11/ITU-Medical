from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Time,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HorarioMedico(Base):
    __tablename__ = "horario_medico"
    __table_args__ = (
        CheckConstraint("dia_semana BETWEEN 0 AND 6", name="dia_semana"),
        CheckConstraint("hora_inicio < hora_fin", name="rango_horario"),
        CheckConstraint("duracion_minutos > 0", name="duracion_positiva"),
        Index("ix_horario_medico_dia", "id_medico", "dia_semana"),
    )

    id_horario: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    id_medico: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("medico.id_medico", name="fk_horario_medico"),
        nullable=False,
    )
    dia_semana: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    duracion_minutos: Mapped[int] = mapped_column(Integer, nullable=False)
    vigente_desde: Mapped[date | None] = mapped_column(Date)
    vigente_hasta: Mapped[date | None] = mapped_column(Date)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=func.now(),
    )
