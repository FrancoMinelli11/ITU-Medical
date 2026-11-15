"""Pruebas de gestión y vigencia de Usuario rojo (RF-16, RN-20..RN-22, RN-36).

Cubre:
- P-24: Recepción clasifica a paciente como Usuario rojo (30 días, notificación enviada).
- P-25: Paciente clasificado no puede reservar por la web (recibe 403 USUARIO_ROJO).
- P-26: Restricción vencida permite reserva web sin necesidad de cron (evaluación dinámica).
- Levantamiento de restricción y trazabilidad en AUDITORIA.
"""

from __future__ import annotations

from datetime import datetime as dt
from datetime import time as dtime
from datetime import timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.core.timezone import LOCAL_TZ, now_utc, to_local
from app.db.models.auditoria import Auditoria
from app.db.models.enums import RolUsuario
from app.db.models.medico import Medico
from app.db.models.paciente import Paciente
from app.db.models.restriccion_usuario import RestriccionUsuario
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
        nombre="Recepcionista",
        apellido="Hospital",
    )
    await sesion.login(usuario.dni, PASSWORD)
    return usuario


async def _crear_medico_con_agenda(client: Any, sesion_admin: Any, fabrica: Any) -> str:
    res_esp = await client.post(
        "/api/v1/especialidades",
        json={"nombre": f"Esp-{uuid4().hex[:8]}"},
        headers=sesion_admin.mutacion(),
    )
    id_esp = res_esp.json()["id_especialidad"]

    usuario_medico = await fabrica.crear(
        rol=RolUsuario.MEDICO,
        password=PASSWORD,
        email=f"med-{uuid4().hex[:6]}@example.com",
    )
    async with SessionLocal() as db:
        medico = Medico(
            id_usuario=usuario_medico.id_usuario,
            id_especialidad=id_esp,
            matricula=f"MN-{uuid4().hex[:6]}",
            activo=True,
        )
        db.add(medico)
        await db.commit()
        id_medico = str(medico.id_medico)

    horarios = [
        {
            "dia_semana": dia,
            "hora_inicio": "08:00:00",
            "hora_fin": "18:00:00",
            "duracion_minutos": 30,
        }
        for dia in range(7)
    ]
    await client.put(
        f"/api/v1/medicos/{id_medico}/horarios",
        json={"horarios": horarios},
        headers=sesion_admin.mutacion(),
    )
    return id_medico


def _calcular_slot_futuro(dias: int = 2, hora: int = 10, minuto: int = 0) -> dt:
    base = (to_local(now_utc()) + timedelta(days=dias)).date()
    return dt.combine(base, dtime(hora, minuto), tzinfo=LOCAL_TZ).astimezone()


async def test_clasificar_usuario_rojo_ok(
    client: Any, sesion: Any, fabrica: Any, buzon: Any
) -> None:
    """P-24, RF-16, RN-20: Recepción clasifica a paciente como Usuario rojo (30 días)."""
    recep = await _crear_staff(fabrica, sesion, RolUsuario.RECEPCIONISTA)
    paciente_user = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    async with SessionLocal() as db:
        id_paciente = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == paciente_user.id_usuario)
        )
        assert id_paciente is not None

    # Recepción clasifica al paciente
    await sesion.login(recep.dni, PASSWORD)
    payload = {
        "id_paciente": str(id_paciente),
        "motivo": "Acumulación de 3 ausencias sin aviso previo",
        "dias_vigencia": 30,
    }
    res = await client.post("/api/v1/restricciones", json=payload, headers=sesion.mutacion())
    assert res.status_code == 201, res.text
    datos = res.json()
    assert datos["activa"] is True
    assert datos["vigente"] is True
    assert datos["paciente_dni"] == paciente_user.dni
    id_restriccion = datos["id_restriccion"]

    # Verificar persistencia en base y auditoría
    async with SessionLocal() as db:
        rest = await db.get(RestriccionUsuario, id_restriccion)
        assert rest is not None
        assert rest.activa is True
        assert rest.motivo == "Acumulación de 3 ausencias sin aviso previo"

        audit = await db.scalar(
            select(Auditoria).where(
                Auditoria.accion == "ALTA_RESTRICCION_USUARIO",
                Auditoria.entidad_id == rest.id_restriccion,
            )
        )
        assert audit is not None

    # Verificar que se envió la notificación al buzón
    envios = buzon.de(paciente_user.email)
    assert len(envios) == 1
    assert "Información sobre el estado de tu cuenta" in envios[0]["asunto"]


async def test_clasificar_usuario_rojo_duplicada_rechazada(
    client: Any, sesion: Any, fabrica: Any
) -> None:
    """Rechaza segunda restricción si ya hay una activa vigente (409 USUARIO_YA_RESTRINGIDO)."""
    recep = await _crear_staff(fabrica, sesion, RolUsuario.RECEPCIONISTA)
    paciente_user = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    async with SessionLocal() as db:
        id_paciente = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == paciente_user.id_usuario)
        )

    await sesion.login(recep.dni, PASSWORD)
    payload = {
        "id_paciente": str(id_paciente),
        "motivo": "Primera infracción",
        "dias_vigencia": 30,
    }
    res1 = await client.post("/api/v1/restricciones", json=payload, headers=sesion.mutacion())
    assert res1.status_code == 201

    # Segunda restricción mientras la primera sigue vigente
    res2 = await client.post("/api/v1/restricciones", json=payload, headers=sesion.mutacion())
    assert res2.status_code == 409
    assert res2.json()["code"] == "USUARIO_YA_RESTRINGIDO"


async def test_reserva_web_rechazada_y_recepcion_permitida(
    client: Any, sesion: Any, fabrica: Any
) -> None:
    """P-25, RF-16, RN-21: Usuario rojo no puede reservar vía web pero recepción sí."""
    await _admin_user(fabrica, sesion)
    id_medico = await _crear_medico_con_agenda(client, sesion, fabrica)
    recep = await _crear_staff(fabrica, sesion, RolUsuario.RECEPCIONISTA)

    paciente_user = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    async with SessionLocal() as db:
        id_paciente = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == paciente_user.id_usuario)
        )

    # Recepción clasifica como usuario rojo
    await sesion.login(recep.dni, PASSWORD)
    await client.post(
        "/api/v1/restricciones",
        json={
            "id_paciente": str(id_paciente),
            "motivo": "Ausencias reiteradas",
            "dias_vigencia": 30,
        },
        headers=sesion.mutacion(),
    )

    # 1. Paciente intenta reservar vía web -> 403 USUARIO_ROJO_RESTRINGIDO
    await sesion.login(paciente_user.dni, PASSWORD)
    slot1 = _calcular_slot_futuro(dias=2, hora=10, minuto=0)
    res_web = await client.post(
        "/api/v1/turnos",
        json={"id_medico": id_medico, "fecha_hora": slot1.isoformat()},
        headers=sesion.mutacion(),
    )
    assert res_web.status_code == 403
    assert res_web.json()["code"] == "USUARIO_ROJO_RESTRINGIDO"

    # 2. Recepción reserva presencialmente en nombre del paciente -> 201 OK
    await sesion.login(recep.dni, PASSWORD)
    slot2 = _calcular_slot_futuro(dias=2, hora=10, minuto=30)
    res_recep = await client.post(
        "/api/v1/turnos/recepcion",
        json={
            "dni_paciente": paciente_user.dni,
            "id_medico": id_medico,
            "fecha_hora": slot2.isoformat(),
        },
        headers=sesion.mutacion(),
    )
    assert res_recep.status_code == 201
    assert res_recep.json()["estado"] == "RESERVADO"


async def test_restriccion_vencida_permite_reserva_sin_cron(
    client: Any, sesion: Any, fabrica: Any
) -> None:
    """P-26, RN-36: Restricción con fecha_fin pasada se evalúa dinámicamente como inactiva."""
    admin = await _admin_user(fabrica, sesion)
    id_medico = await _crear_medico_con_agenda(client, sesion, fabrica)

    paciente_user = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    async with SessionLocal() as db:
        id_paciente = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == paciente_user.id_usuario)
        )
        assert id_paciente is not None

        # Insertar restricción ya expirada hace 2 horas
        restriccion = RestriccionUsuario(
            id_usuario=paciente_user.id_usuario,
            motivo="Sanción expirada",
            fecha_inicio=now_utc() - timedelta(days=30),
            fecha_fin=now_utc() - timedelta(hours=2),
            activa=True,
            id_usuario_creador=admin.id_usuario,
        )
        db.add(restriccion)
        await db.commit()

    # Paciente consulta su estado
    await sesion.login(paciente_user.dni, PASSWORD)
    res_estado = await client.get(
        f"/api/v1/restricciones/paciente/{id_paciente}",
        headers=sesion.bearer,
    )
    assert res_estado.status_code == 200
    assert res_estado.json()["es_usuario_rojo"] is False

    # Paciente reserva turno web con normalidad
    slot = _calcular_slot_futuro(dias=3, hora=11, minuto=0)
    res_reserva = await client.post(
        "/api/v1/turnos",
        json={"id_medico": id_medico, "fecha_hora": slot.isoformat()},
        headers=sesion.mutacion(),
    )
    assert res_reserva.status_code == 201, res_reserva.text
    assert res_reserva.json()["estado"] == "RESERVADO"


async def test_levantar_restriccion_administrativa(client: Any, sesion: Any, fabrica: Any) -> None:
    """Recepción levanta anticipadamente una restricción de Usuario rojo."""
    recep = await _crear_staff(fabrica, sesion, RolUsuario.RECEPCIONISTA)
    paciente_user = await fabrica.crear(
        rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True
    )
    async with SessionLocal() as db:
        id_paciente = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == paciente_user.id_usuario)
        )

    # 1. Crear restricción
    await sesion.login(recep.dni, PASSWORD)
    res_crear = await client.post(
        "/api/v1/restricciones",
        json={
            "id_paciente": str(id_paciente),
            "motivo": "Error administrativo inicial",
            "dias_vigencia": 30,
        },
        headers=sesion.mutacion(),
    )
    assert res_crear.status_code == 201
    id_restriccion = res_crear.json()["id_restriccion"]

    # 2. Levantar la restricción
    res_levantar = await client.post(
        f"/api/v1/restricciones/{id_restriccion}/levantar",
        headers=sesion.mutacion(),
    )
    assert res_levantar.status_code == 200
    datos = res_levantar.json()
    assert datos["activa"] is False
    assert datos["vigente"] is False

    # 3. Verificar estado del paciente
    res_estado = await client.get(
        f"/api/v1/restricciones/paciente/{id_paciente}",
        headers=sesion.bearer,
    )
    assert res_estado.status_code == 200
    assert res_estado.json()["es_usuario_rojo"] is False


async def test_permisos_restricciones(client: Any, sesion: Any, fabrica: Any) -> None:
    """Verifica permisos de acceso en endpoints de restricciones."""
    p1 = await fabrica.crear(rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True)
    p2 = await fabrica.crear(rol=RolUsuario.PACIENTE, password=PASSWORD, email_verificado=True)

    async with SessionLocal() as db:
        id_p1 = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == p1.id_usuario)
        )
        id_p2 = await db.scalar(
            select(Paciente.id_paciente).where(Paciente.id_usuario == p2.id_usuario)
        )

    await sesion.login(p1.dni, PASSWORD)

    # Paciente 1 intenta clasificar a Paciente 2 -> 403
    res_post = await client.post(
        "/api/v1/restricciones",
        json={"id_paciente": str(id_p2), "motivo": "No autorizado", "dias_vigencia": 30},
        headers=sesion.mutacion(),
    )
    assert res_post.status_code == 403

    # Paciente 1 intenta consultar estado de Paciente 2 -> 403
    res_get_otro = await client.get(
        f"/api/v1/restricciones/paciente/{id_p2}",
        headers=sesion.bearer,
    )
    assert res_get_otro.status_code == 403

    # Paciente 1 consulta su propio estado -> 200 OK
    res_propio = await client.get(
        f"/api/v1/restricciones/paciente/{id_p1}",
        headers=sesion.bearer,
    )
    assert res_propio.status_code == 200
    assert res_propio.json()["es_usuario_rojo"] is False
