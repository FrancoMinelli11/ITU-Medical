"""Pruebas de la matriz de permisos y control de acceso server-side (RF-03, RNF-03, P-29).

Cubre:
- P-29: Verificación de que cada rol acceda únicamente a los endpoints para los que
  tiene autorización en el servidor, recibiendo 403 Forbidden los no autorizados.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.db.models.enums import RolUsuario

PASSWORD = "Password123!"


async def _crear_usuario_rol(fabrica: Any, sesion: Any, rol: RolUsuario) -> Any:
    usr = await fabrica.crear(
        rol=rol,
        password=PASSWORD,
        email_verificado=True,
    )
    await sesion.login(usr.dni, PASSWORD)
    return usr


async def test_permisos_pacientes_restringido(client: Any, sesion: Any, fabrica: Any) -> None:
    """Solo Staff (Recepción/Admin) puede listar o crear pacientes desde recepción."""
    paciente = await _crear_usuario_rol(fabrica, sesion, RolUsuario.PACIENTE)
    medico = await _crear_usuario_rol(fabrica, sesion, RolUsuario.MEDICO)

    # 1. Paciente intenta listar pacientes -> 403
    await sesion.login(paciente.dni, PASSWORD)
    res = await client.get("/api/v1/pacientes", headers=sesion.bearer)
    assert res.status_code == 403

    # Paciente intenta crear paciente desde recepción -> 403
    res_alta = await client.post(
        "/api/v1/pacientes",
        json={"dni": "45111222", "nombre": "Test", "apellido": "User"},
        headers=sesion.mutacion(),
    )
    assert res_alta.status_code == 403

    # 2. Médico intenta listar pacientes -> 403
    await sesion.login(medico.dni, PASSWORD)
    res_med = await client.get("/api/v1/pacientes", headers=sesion.bearer)
    assert res_med.status_code == 403


async def test_permisos_especialidades_y_medicos(client: Any, sesion: Any, fabrica: Any) -> None:
    """Solo Administrador puede crear especialidades o médicos."""
    paciente = await _crear_usuario_rol(fabrica, sesion, RolUsuario.PACIENTE)
    recep = await _crear_usuario_rol(fabrica, sesion, RolUsuario.RECEPCIONISTA)
    medico = await _crear_usuario_rol(fabrica, sesion, RolUsuario.MEDICO)

    for rol_user in (paciente, recep, medico):
        await sesion.login(rol_user.dni, PASSWORD)
        # Crear especialidad -> 403
        res_esp = await client.post(
            "/api/v1/especialidades",
            json={"nombre": f"Esp-{uuid4().hex[:6]}"},
            headers=sesion.mutacion(),
        )
        assert res_esp.status_code == 403

        # Crear médico -> 403
        res_med = await client.post(
            "/api/v1/medicos",
            json={
                "dni": f"3{uuid4().int % 8999999 + 1000000}",
                "nombre": "Doc",
                "apellido": "Test",
                "email": f"m-{uuid4().hex[:6]}@example.com",
                "id_especialidad": str(uuid4()),
            },
            headers=sesion.mutacion(),
        )
        assert res_med.status_code == 403


async def test_permisos_recepcion_restringido(client: Any, sesion: Any, fabrica: Any) -> None:
    """Solo Recepción y Admin pueden registrar llegadas o cierre de jornada."""
    paciente = await _crear_usuario_rol(fabrica, sesion, RolUsuario.PACIENTE)
    medico = await _crear_usuario_rol(fabrica, sesion, RolUsuario.MEDICO)

    for rol_user in (paciente, medico):
        await sesion.login(rol_user.dni, PASSWORD)

        # Registrar llegada -> 403
        res_llegada = await client.post(
            f"/api/v1/recepcion/turnos/{uuid4()}/llegada",
            headers=sesion.mutacion(),
        )
        assert res_llegada.status_code == 403

        # Cierre de jornada -> 403
        res_cierre = await client.post(
            "/api/v1/recepcion/cierre-jornada",
            headers=sesion.mutacion(),
        )
        assert res_cierre.status_code == 403


async def test_permisos_atencion_y_notas(client: Any, sesion: Any, fabrica: Any) -> None:
    """Solo personal médico o admin puede registrar atención y notas médicas."""
    paciente = await _crear_usuario_rol(fabrica, sesion, RolUsuario.PACIENTE)
    recep = await _crear_usuario_rol(fabrica, sesion, RolUsuario.RECEPCIONISTA)

    for rol_user in (paciente, recep):
        await sesion.login(rol_user.dni, PASSWORD)

        # Atender turno -> 403
        res_atender = await client.post(
            f"/api/v1/turnos/{uuid4()}/atender",
            headers=sesion.mutacion(),
        )
        assert res_atender.status_code == 403

        # Crear nota de seguimiento -> 403
        res_nota = await client.post(
            "/api/v1/notas",
            json={"id_paciente": str(uuid4()), "contenido": "Nota clínica"},
            headers=sesion.mutacion(),
        )
        assert res_nota.status_code == 403


async def test_permisos_restricciones(client: Any, sesion: Any, fabrica: Any) -> None:
    """Solo staff puede clasificar como Usuario rojo o levantar restricciones."""
    paciente = await _crear_usuario_rol(fabrica, sesion, RolUsuario.PACIENTE)
    medico = await _crear_usuario_rol(fabrica, sesion, RolUsuario.MEDICO)

    for rol_user in (paciente, medico):
        await sesion.login(rol_user.dni, PASSWORD)

        # Clasificar usuario rojo -> 403
        res_clasificar = await client.post(
            "/api/v1/restricciones",
            json={
                "id_paciente": str(uuid4()),
                "motivo": "Intento no autorizado",
                "dias_vigencia": 30,
            },
            headers=sesion.mutacion(),
        )
        assert res_clasificar.status_code == 403

        # Levantar restricción -> 403
        res_levantar = await client.post(
            f"/api/v1/restricciones/{uuid4()}/levantar",
            headers=sesion.mutacion(),
        )
        assert res_levantar.status_code == 403
