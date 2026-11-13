from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Auditoria(Base):
    __tablename__ = "auditoria"
    __table_args__ = (
        Index("ix_auditoria_fecha", "fecha_hora"),
        Index("ix_auditoria_entidad", "entidad", "entidad_id"),
    )

    id_auditoria: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    id_usuario: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("usuario.id_usuario", name="fk_auditoria_usuario")
    )
    accion: Mapped[str] = mapped_column(String(80), nullable=False)
    entidad: Mapped[str] = mapped_column(String(80), nullable=False)
    entidad_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    datos_antes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    datos_despues: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    ip: Mapped[str | None] = mapped_column(INET)
    request_id: Mapped[str | None] = mapped_column(String(64))
