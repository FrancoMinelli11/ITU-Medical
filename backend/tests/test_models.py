from app.db import models  # noqa: F401
from app.db.base import Base


def test_tablas_del_der_registradas() -> None:
    esperadas = {
        "usuario",
        "paciente",
        "medico",
        "especialidad",
        "horario_medico",
        "bloqueo_agenda",
        "turno",
        "nota_seguimiento",
        "solicitud_cancelacion",
        "restriccion_usuario",
        "auditoria",
        "verificacion_email",
        "recuperacion_password",
        "notificacion",
    }
    assert esperadas <= set(Base.metadata.tables)
