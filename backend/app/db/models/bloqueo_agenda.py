from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BloqueoAgenda(Base):
    __tablename__ = "bloqueo_agenda"
    __table_args__ = (
        CheckConstraint("fin > inicio", name="rango_bloqueo"),
        Index("ix_bloqueo_medico_rango", "id_medico", "inicio", "fin"),
    )

    id_bloqueo: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    id_medico: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("medico.id_medico", name="fk_bloqueo_medico"),
        nullable=False,
    )
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    id_usuario_creador: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id_usuario", name="fk_bloqueo_usuario_creador"),
        nullable=False,
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
