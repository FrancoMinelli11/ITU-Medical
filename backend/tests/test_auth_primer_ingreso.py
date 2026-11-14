"""P-33 / C3: cuentas creadas por recepción (contraseña temporal = DNI).

Decisión Q1 = A: el DNI literal es la contraseña temporal y queda **exento** de
RN-28 (7-8 caracteres, sin letra), con cambio obligatorio en el primer ingreso
(RN-29). Es una excepción documentada: RF-02, CU-13 y P-04 la exigen así.
"""

from __future__ import annotations

import pytest

from app.api.deps import require_password_actualizada
from app.core.exceptions import ApiError
from app.db.models.enums import RolUsuario
from app.db.models.usuario import Usuario
from app.db.session import SessionLocal


async def test_login_con_password_temporal(client, sesion, fabrica) -> None:
    usuario = await fabrica.crear(
        password=None,
        debe_cambiar_password=True,
        rol=RolUsuario.RECEPCIONISTA,
        nombre="Camila",
        apellido="Pérez",
    )

    # RN-28 pide >= 10 con letra y dígito: el DNI no la cumple a propósito.
    assert len(usuario.dni) == 8

    datos = await sesion.login(usuario.dni, usuario.dni)

    assert datos["debe_cambiar_password"] is True
    assert datos["usuario"]["rol"] == "RECEPCIONISTA"
    assert datos["usuario"]["email_verificado"] is True


async def test_me_responde_200_con_el_flag(client, sesion, fabrica) -> None:
    """C3: `/auth/me` debe funcionar o el SPA no puede saber a dónde redirigir."""
    usuario = await fabrica.crear(password=None, debe_cambiar_password=True)
    await sesion.login(usuario.dni, usuario.dni)

    respuesta = await client.get("/api/v1/auth/me", headers=sesion.bearer)

    assert respuesta.status_code == 200
    assert respuesta.json()["debe_cambiar_password"] is True


async def test_dependencia_bloquea_el_resto_de_endpoints(fabrica) -> None:
    """El mismo 403 se ve e2e contra `/pacientes` en `test_pacientes.py`."""
    usuario = await fabrica.crear(password=None, debe_cambiar_password=True)

    with pytest.raises(ApiError) as excinfo:
        await require_password_actualizada(usuario)

    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "CAMBIO_PASSWORD_REQUERIDO"


async def test_dependencia_deja_pasar_sin_el_flag(fabrica) -> None:
    usuario = await fabrica.crear(password="Password123!")

    assert await require_password_actualizada(usuario) is usuario


async def test_el_flag_vive_en_la_fila_no_en_el_jwt(client, sesion, fabrica) -> None:
    """Se lee de `USUARIO` en cada request: no queda pegado 15 minutos."""
    usuario = await fabrica.crear(password=None, debe_cambiar_password=True)
    await sesion.login(usuario.dni, usuario.dni)

    async with SessionLocal() as session:
        fila = await session.get(Usuario, usuario.id_usuario)
        assert fila is not None
        fila.debe_cambiar_password = False
        await session.commit()

    respuesta = await client.get("/api/v1/auth/me", headers=sesion.bearer)

    assert respuesta.json()["debe_cambiar_password"] is False
