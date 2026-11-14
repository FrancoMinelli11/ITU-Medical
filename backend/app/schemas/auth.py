"""Contratos de entrada y salida de `/auth`."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import RolUsuario

DNI_PATTERN = r"^\d{7,8}$"


class LoginRequest(BaseModel):
    """El DNI va como texto siempre (RN-30): nunca `int`, perdería ceros."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    dni: str = Field(min_length=7, max_length=8, pattern=DNI_PATTERN)
    # En login no se valida la política de contraseñas: las cuentas creadas por
    # recepción usan el DNI como contraseña temporal (decisión Q1 = A).
    password: str = Field(min_length=1, max_length=128)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: UUID
    dni: str
    # `str` y no `EmailStr`: el dato ya está validado al registrarse, y
    # `email-validator` rechaza dominios internos como `turnos.local` (seed).
    email: str
    nombre: str
    apellido: str
    rol: RolUsuario
    email_verificado: bool
    debe_cambiar_password: bool
    ultimo_login: datetime | None = None
    telefono: str | None = None
    fecha_nacimiento: date | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: UsuarioOut
    debe_cambiar_password: bool


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: UsuarioOut
