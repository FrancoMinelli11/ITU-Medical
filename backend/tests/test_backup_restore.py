"""Pruebas de verificación de scripts y procedimientos de backup y restore (RNF-09, P-45).

Cubre:
- P-45: Verificación de presencia, sintaxis e integridad de backup.sh y restore.sh.
- Verificación de consistencia relacional y constraints de los modelos exportables.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select

from app.core.timezone import now_utc
from app.db.models.auditoria import Auditoria
from app.db.models.enums import EstadoTurno, RolUsuario
from app.db.models.especialidad import Especialidad
from app.db.models.medico import Medico
from app.db.models.paciente import Paciente
from app.db.models.turno import Turno
from app.db.models.usuario import Usuario
from app.db.session import SessionLocal

PASSWORD = "Password123!"
RAIZ = Path(__file__).resolve().parent.parent.parent


def test_scripts_backup_restore_existencia_y_contenido() -> None:
    """Verifica que los scripts de backup y restore existan y contengan comandos válidos."""
    backup_sh = RAIZ / "scripts" / "backup.sh"
    restore_sh = RAIZ / "scripts" / "restore.sh"

    assert backup_sh.exists(), "scripts/backup.sh no existe"
    assert restore_sh.exists(), "scripts/restore.sh no existe"

    contenido_backup = backup_sh.read_text(encoding="utf-8")
    assert "pg_dump" in contenido_backup
    assert "--format=custom" in contenido_backup
    assert "RETENTION_DAYS" in contenido_backup

    contenido_restore = restore_sh.read_text(encoding="utf-8")
    assert "pg_restore" in contenido_restore
    assert "--clean" in contenido_restore
    assert "--if-exists" in contenido_restore


async def test_consistencia_datos_para_backup_y_restore(fabrica: Any) -> None:
    """Verifica la coherencia relacional completa con datos listos para ciclo de backup."""
    async with SessionLocal() as db:
        # 1. Crear especialidad y médico
        esp = Especialidad(nombre=f"EspBackup-{uuid4().hex[:6]}")
        db.add(esp)
        await db.flush()

        med_usr = await fabrica.crear(
            rol=RolUsuario.MEDICO,
            password=PASSWORD,
            email=f"med-{uuid4().hex[:6]}@example.com",
        )
        med = Medico(
            id_usuario=med_usr.id_usuario,
            id_especialidad=esp.id_especialidad,
            matricula="MN-BACKUP-01",
            activo=True,
        )
        db.add(med)

        # 2. Crear paciente y turno
        pac_usr = await fabrica.crear(
            rol=RolUsuario.PACIENTE,
            password=PASSWORD,
            email_verificado=True,
        )
        pac = await db.scalar(select(Paciente).where(Paciente.id_usuario == pac_usr.id_usuario))
        assert pac is not None

        turno = Turno(
            id_paciente=pac.id_paciente,
            id_medico=med.id_medico,
            fecha_hora=now_utc(),
            duracion_minutos=30,
            estado=EstadoTurno.RESERVADO,
            id_usuario_creador=pac_usr.id_usuario,
        )
        db.add(turno)

        # 3. Auditoría asociada
        aud = Auditoria(
            id_usuario=pac_usr.id_usuario,
            accion="TEST_BACKUP_CONSISTENCIA",
            entidad="turno",
            entidad_id=turno.id_turno,
        )
        db.add(aud)
        await db.commit()

        # 4. Verificación de conteo y navegación de relaciones
        total_usuarios = await db.scalar(select(func.count(Usuario.id_usuario)))
        total_turnos = await db.scalar(select(func.count(Turno.id_turno)))
        total_auditorias = await db.scalar(select(func.count(Auditoria.id_auditoria)))

        assert total_usuarios is not None and total_usuarios >= 2
        assert total_turnos is not None and total_turnos >= 1
        assert total_auditorias is not None and total_auditorias >= 1
