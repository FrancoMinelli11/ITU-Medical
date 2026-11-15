"""Pruebas de atención de turnos y notas de seguimiento (RF-13, RF-14).

Cubre:
- RF-13, CU-08, T-RF13: Médico atiende turno en EN_ESPERA -> ATENDIDO.
- P-22: Creación y modificación de notas médicas por el profesional.
- P-23: Confidencialidad clínica (acceso restringido a rol MEDICO/ADMIN).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.core.timezone import now_utc, to_local
from app.db.models.auditoria import Auditoria
from app.db.models.enums import EstadoTurno, RolUsuario
from app.db.models.especialidad import Especialidad
from app.db.models.medico import Medico
from app.db.models.paciente import Paciente
from app.db.models.turno import Turno
from app.db.session import SessionLocal

PASSWORD = "Password123!"


async def _admin_user(fabrica: Any, sesion: Any) -> Any:
    usuario = await fabrica.crear(
        rol=RolUsuario.ADMINISTRADOR,
        password=PASSWORD,
        nombre="Admin",
        apellido="General",
    )
    await sesion.login(usuario.dni, PASSWORD)
    return usuario


async def _crear_staff(
    fabrica: Any, sesion: Any, rol: RolUsuario = RolUsuario.RECEPCIONISTA
) -> Any:
    usuario = await fabrica.crear(
        rol=rol,
        password=PASSWORD,
        nombre="Staff",
        apellido="Hospital",
    )
    await sesion.login(usuario.dni, PASSWORD)
    return usuario


async def _crear_medico_completo(
    fabrica: Any, sesion: Any, nombre: str = "DrHouse"
) -> tuple[Any, str]:
    """Crea un usuario con rol MEDICO, su fila en MEDICO y su especialidad."""
    async with SessionLocal() as db:
        esp = Especialidad(nombre=f"Esp-{uuid4().hex[:8]}")
        db.add(esp)
        await db.flush()

        usuario = await fabrica.crear(
            rol=RolUsuario.MEDICO,
            password=PASSWORD,
            nombre=nombre,
            apellido="Clínico",
        )

        medico = Medico(
            id_usuario=usuario.id_usuario,
            id_especialidad=esp.id_especialidad,
            matricula=f"MN-{uuid4().hex[:6]}",
            activo=True,
        )
        db.add(medico)
        await db.commit()
        id_medico = str(medico.id_medico)

    await sesion.login(usuario.dni, PASSWORD)
    return usuario, id_medico


async def test_atender_turno_ok(client: Any, sesion: Any, fabrica: Any) -> None:
    """RF-13, CU-08, T-RF13: El médico atiende turno en espera (EN_ESPERA -> ATENDIDO)."""
    # 1. Crear médico y paciente
    med_user, id_medico = await _crear_medico_completo(fabrica, sesion)

    paciente_user = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    async with SessionLocal() as db:
        id_paciente = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == paciente_user.id_usuario)
        )
        assert id_paciente is not None

        # Turno en estado EN_ESPERA con llegada registrada
        fecha_turno = to_local(now_utc()) + timedelta(hours=1)
        turno = Turno(
            id_paciente=id_paciente,
            id_medico=id_medico,
            fecha_hora=fecha_turno,
            duracion_minutos=30,
            estado=EstadoTurno.EN_ESPERA,
            fecha_hora_llegada=now_utc(),
        )
        db.add(turno)
        await db.commit()
        id_turno = str(turno.id_turno)

    # 2. Login como médico y atender
    await sesion.login(med_user.dni, PASSWORD)
    res = await client.post(
        f"/api/v1/turnos/{id_turno}/atender",
        headers=sesion.mutacion(),
    )
    assert res.status_code == 200, res.text
    datos = res.json()
    assert datos["estado"] == "ATENDIDO"

    # 3. Verificar persistencia y auditoría
    async with SessionLocal() as db:
        t_db = await db.get(Turno, turno.id_turno)
        assert t_db is not None
        assert t_db.estado == EstadoTurno.ATENDIDO

        audit = await db.scalar(
            select(Auditoria).where(
                Auditoria.accion == "ATENCION_TURNO",
                Auditoria.entidad_id == turno.id_turno,
            )
        )
        assert audit is not None


async def test_atender_turno_invalido_falla(client: Any, sesion: Any, fabrica: Any) -> None:
    """Transición inválida si el paciente no anunció llegada o médico no asignado."""
    med1_user, id_med1 = await _crear_medico_completo(fabrica, sesion, nombre="DocUno")
    med2_user, _id_med2 = await _crear_medico_completo(fabrica, sesion, nombre="DocDos")

    paciente_user = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    async with SessionLocal() as db:
        id_paciente = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == paciente_user.id_usuario)
        )
        # Turno en RESERVADO (no llegó)
        turno = Turno(
            id_paciente=id_paciente,
            id_medico=id_med1,
            fecha_hora=to_local(now_utc()) + timedelta(hours=2),
            duracion_minutos=30,
            estado=EstadoTurno.RESERVADO,
        )
        db.add(turno)
        await db.commit()
        id_turno = str(turno.id_turno)

    # Intentar atender sin llegada -> 400 Transición no permitida
    await sesion.login(med1_user.dni, PASSWORD)
    res_sin_llegada = await client.post(
        f"/api/v1/turnos/{id_turno}/atender",
        headers=sesion.mutacion(),
    )
    assert res_sin_llegada.status_code == 400
    assert res_sin_llegada.json()["codigo"] == "TRANSICION_INVALIDA"

    # Ahora poner en EN_ESPERA
    async with SessionLocal() as db:
        t = await db.get(Turno, turno.id_turno)
        assert t is not None
        t.estado = EstadoTurno.EN_ESPERA
        t.fecha_hora_llegada = now_utc()
        await db.commit()

    # Médico 2 intenta atender turno de Médico 1 -> 403
    await sesion.login(med2_user.dni, PASSWORD)
    res_otro_med = await client.post(
        f"/api/v1/turnos/{id_turno}/atender",
        headers=sesion.mutacion(),
    )
    assert res_otro_med.status_code == 403
    assert res_otro_med.json()["codigo"] == "ACCESO_DENEGADO"


async def test_crear_y_modificar_nota_medica_ok(client: Any, sesion: Any, fabrica: Any) -> None:
    """P-22, RF-14: El médico registra y luego modifica una anotación médica de seguimiento."""
    med_user, id_medico = await _crear_medico_completo(fabrica, sesion)
    paciente_user = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    async with SessionLocal() as db:
        id_paciente = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == paciente_user.id_usuario)
        )
        assert id_paciente is not None

    await sesion.login(med_user.dni, PASSWORD)

    # 1. Crear nota médica
    res_crear = await client.post(
        "/api/v1/notas",
        json={
            "id_paciente": str(id_paciente),
            "contenido": "Paciente responde bien al tratamiento de control.",
        },
        headers=sesion.mutacion(),
    )
    assert res_crear.status_code == 201, res_crear.text
    nota_creada = res_crear.json()
    id_nota = nota_creada["id_nota"]
    assert nota_creada["contenido"] == "Paciente responde bien al tratamiento de control."
    assert nota_creada["id_medico"] == id_medico

    # 2. Modificar la nota
    res_mod = await client.put(
        f"/api/v1/notas/{id_nota}",
        json={"contenido": "Paciente responde bien al tratamiento. Se indica seguimiento mensual."},
        headers=sesion.mutacion(),
    )
    assert res_mod.status_code == 200, res_mod.text
    assert "seguimiento mensual" in res_mod.json()["contenido"]

    # 3. Listar notas del paciente
    res_lista = await client.get(
        f"/api/v1/notas/paciente/{id_paciente}",
        headers=sesion.mutacion(),
    )
    assert res_lista.status_code == 200
    items = res_lista.json()
    assert len(items) == 1
    assert items[0]["id_nota"] == id_nota


async def test_acceso_notas_medicas_restringido(client: Any, sesion: Any, fabrica: Any) -> None:
    """P-23, RF-14: Confidencialidad clínica: paciente o recepción no acceden a notas médicas."""
    med1_user, id_med1 = await _crear_medico_completo(fabrica, sesion, nombre="DocAutor")
    med2_user, _ = await _crear_medico_completo(fabrica, sesion, nombre="DocSegundo")

    paciente_user = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    recep_user = await _crear_staff(fabrica, sesion, RolUsuario.RECEPCIONISTA)

    async with SessionLocal() as db:
        id_paciente = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == paciente_user.id_usuario)
        )
        assert id_paciente is not None

    # Médico crea una nota
    await sesion.login(med1_user.dni, PASSWORD)
    res_crear = await client.post(
        "/api/v1/notas",
        json={
            "id_paciente": str(id_paciente),
            "contenido": "Nota estrictamente clínica y confidencial.",
        },
        headers=sesion.mutacion(),
    )
    assert res_crear.status_code == 201
    id_nota = res_crear.json()["id_nota"]

    # 1. Paciente intenta leer notas -> 403
    await sesion.login(paciente_user.dni, PASSWORD)
    res_paciente_get = await client.get(f"/api/v1/notas/paciente/{id_paciente}")
    assert res_paciente_get.status_code == 403

    # Paciente intenta crear nota -> 403
    res_paciente_post = await client.post(
        "/api/v1/notas",
        json={"id_paciente": str(id_paciente), "contenido": "Nota de paciente"},
        headers=sesion.mutacion(),
    )
    assert res_paciente_post.status_code == 403

    # 2. Recepcionista intenta leer notas -> 403
    await sesion.login(recep_user.dni, PASSWORD)
    res_recep_get = await client.get(f"/api/v1/notas/paciente/{id_paciente}")
    assert res_recep_get.status_code == 403

    # 3. Otro médico intenta modificar la nota de otro médico -> 403
    await sesion.login(med2_user.dni, PASSWORD)
    res_otro_med_put = await client.put(
        f"/api/v1/notas/{id_nota}",
        json={"contenido": "Intento de modificación no autorizado."},
        headers=sesion.mutacion(),
    )
    assert res_otro_med_put.status_code == 403
    assert res_otro_med_put.json()["codigo"] == "ACCESO_DENEGADO"
