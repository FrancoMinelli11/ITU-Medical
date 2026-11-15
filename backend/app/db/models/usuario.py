from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import RolUsuario


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = (
        CheckConstraint("dni ~ '^[0-9]{7,8}$'", name="dni_formato"),
        Index("ix_usuario_rol", "rol"),
    )

    id_usuario: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    dni: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolUsuario] = mapped_column(
        Enum(RolUsuario, name="rol_usuario", native_enum=True), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido: Mapped[str] = mapped_column(String(120), nullable=False)
    habilitado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    email_verificado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    debe_cambiar_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=func.now(),
    )
    ultimo_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
