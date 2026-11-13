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
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import EstadoNotificacion, TipoNotificacion


class Notificacion(Base):
    __tablename__ = "notificacion"
    __table_args__ = (
        CheckConstraint("intentos >= 0", name="intentos_no_negativos"),
        Index("ix_notificacion_estado_programada", "estado", "fecha_programada_envio"),
        Index("ix_notificacion_destinatario", "id_usuario_destinatario"),
        Index(
            "uq_notificacion_confirmacion_recordatorio",
            "id_turno",
            "tipo",
            unique=True,
            postgresql_where=text("tipo IN ('CONFIRMACION_TURNO', 'RECORDATORIO_24H')"),
        ),
        Index(
            "uq_notificacion_cancelacion",
            "id_turno",
            "tipo",
            "subtipo",
            unique=True,
            postgresql_where=text("tipo = 'CANCELACION_TURNO'"),
        ),
    )

    id_notificacion: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    id_usuario_destinatario: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id_usuario", name="fk_notificacion_destinatario"),
    )
    tipo: Mapped[TipoNotificacion] = mapped_column(
        Enum(TipoNotificacion, name="tipo_notificacion", native_enum=True),
        nullable=False,
    )
    id_turno: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("turno.id_turno", name="fk_notificacion_turno")
    )
    id_solicitud: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "solicitud_cancelacion.id_solicitud",
            name="fk_notificacion_solicitud",
        ),
    )
    subtipo: Mapped[str | None] = mapped_column(String(32))
    estado: Mapped[EstadoNotificacion] = mapped_column(
        Enum(EstadoNotificacion, name="estado_notificacion", native_enum=True),
        nullable=False,
        server_default=text("'PENDIENTE'::estado_notificacion"),
    )
    intentos: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    ultimo_error: Mapped[str | None] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    fecha_programada_envio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    fecha_envio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
