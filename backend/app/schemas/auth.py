"""Contratos de entrada y salida de `/auth`."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.config import get_settings
from app.db.models.enums import RolUsuario

settings = get_settings()

DNI_PATTERN = r"^\d{7,8}$"

EmailNormalizado = Annotated[EmailStr, AfterValidator(lambda valor: valor.strip().lower())]


def validar_password_fuerte(valor: str) -> str:
    """RN-28: mínimo de caracteres, al menos una letra y un dígito.

    Vive en el schema para que el 400 salga con `errors[].field` como cualquier
    otra validación. El login **no** la aplica: la contraseña temporal de las
    cuentas creadas por recepción es el DNI (excepción a RN-28, decisión Q1 = A).
    """
    if len(valor) < settings.password_min_length:
        raise ValueError(
            f"La contraseña debe tener al menos {settings.password_min_length} caracteres."
        )
    if len(valor) > 128:
        raise ValueError("La contraseña no puede superar los 128 caracteres.")
    if not any(caracter.isalpha() for caracter in valor) or not any(
        caracter.isdigit() for caracter in valor
    ):
        raise ValueError("La contraseña debe combinar letras y números.")
    return valor


PasswordFuerte = Annotated[str, AfterValidator(validar_password_fuerte)]


class LoginRequest(BaseModel):
    """El DNI va como texto siempre (RN-30): nunca `int`, perdería ceros."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    dni: str = Field(min_length=7, max_length=8, pattern=DNI_PATTERN)
    # En login no se valida la política de contraseñas: las cuentas creadas por
    # recepción usan el DNI como contraseña temporal (decisión Q1 = A).
    password: str = Field(min_length=1, max_length=128)


class RegistroRequest(BaseModel):
    """RF-01: alta web de paciente. El correo es obligatorio y único."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    dni: str = Field(min_length=7, max_length=8, pattern=DNI_PATTERN)
    email: EmailNormalizado
    password: PasswordFuerte
    nombre: str = Field(min_length=1, max_length=80)
    apellido: str = Field(min_length=1, max_length=80)
    telefono: str | None = Field(default=None, max_length=30)
    fecha_nacimiento: date | None = None

    @field_validator("nombre", "apellido")
    @classmethod
    def _sin_vacios(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("Este campo no puede quedar vacío.")
        return valor


class VerificarEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    token: str = Field(min_length=16, max_length=200)


class ReenviarVerificacionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailNormalizado


class RecuperarPasswordRequest(BaseModel):
    """RF-21: el par correo + DNI se pide junto (respuesta genérica siempre)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailNormalizado
    dni: str = Field(min_length=7, max_length=8, pattern=DNI_PATTERN)


class RestablecerPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    token: str = Field(min_length=16, max_length=200)
    password: PasswordFuerte


class CambiarPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    password_actual: str = Field(min_length=1, max_length=128)
    password_nueva: PasswordFuerte


class PrimerIngresoRequest(BaseModel):
    """CU-13: la sesión ya está autenticada con la contraseña temporal."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    password_nueva: PasswordFuerte


class VerificacionResponse(BaseModel):
    email_verificado: bool
    mensaje: str


class MensajeResponse(BaseModel):
    mensaje: str


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
