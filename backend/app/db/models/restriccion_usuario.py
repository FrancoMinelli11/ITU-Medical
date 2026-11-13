from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RestriccionUsuario(Base):
    __tablename__ = "restriccion_usuario"
    __table_args__ = (
        CheckConstraint("fecha_fin > fecha_inicio", name="rango_restriccion"),
        Index(
            "uq_restriccion_activa_por_usuario",
            "id_usuario",
            unique=True,
            postgresql_where=text("activa"),
        ),
        Index("ix_restriccion_usuario_fechas", "id_usuario", "fecha_fin"),
    )

    id_restriccion: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    id_usuario: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id_usuario", name="fk_restriccion_usuario"),
        nullable=False,
    )
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    fecha_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    id_usuario_creador: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id_usuario", name="fk_restriccion_usuario_creador"),
        nullable=False,
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
