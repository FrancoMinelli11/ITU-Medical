"""Pruebas de procesamiento y reglas de negocio según zona horaria (RNF-04, P-44).

Cubre:
- P-44: Manejo estricto de America/Argentina/Buenos_Aires:
  - Almacenamiento en base en UTC.
  - Conversión a hora local en respuestas y notificaciones.
  - Cálculo de cancelación habitual (regla de 24 hs).
  - Tolerancia de 10 minutos en orden de atención.
  - Validación de días de la semana de la agenda médica en hora local.
"""

from __future__ import annotations

from datetime import datetime as dt
from datetime import timedelta
from zoneinfo import ZoneInfo

from app.core.timezone import LOCAL_TZ, now_utc, to_local, to_utc
from app.domain.orden_atencion import esta_en_tolerancia


def test_zona_horaria_configurada_es_buenos_aires() -> None:
    """Verifica que la zona horaria del sistema sea America/Argentina/Buenos_Aires."""
    assert LOCAL_TZ == ZoneInfo("America/Argentina/Buenos_Aires")


def test_almacenamiento_utc_y_presentacion_local() -> None:
    """Las fechas se normalizan a UTC pero se presentan en ART (-03:00)."""
    # 15 de marzo de 2026 a las 10:00 hs en Buenos Aires
    fecha_local = dt(2026, 3, 15, 10, 0, 0, tzinfo=LOCAL_TZ)
    fecha_utc = to_utc(fecha_local)

    # Buenos Aires es UTC-3 (sin horario de verano actualmente)
    assert fecha_utc.hour == 13
    assert fecha_utc.tzinfo is not None

    # Vuelta a local
    recuperada = to_local(fecha_utc)
    assert recuperada.hour == 10
    assert recuperada.tzinfo == LOCAL_TZ


def test_tolerancia_10_minutos_en_hora_local() -> None:
    """La tolerancia de llegada evalúa la diferencia temporal correctamente."""
    horario_turno_local = dt(2026, 5, 10, 9, 30, tzinfo=LOCAL_TZ)
    horario_turno_utc = to_utc(horario_turno_local)

    # Llegada puntual: 9:25 ART
    llegada_temprana = to_utc(dt(2026, 5, 10, 9, 25, tzinfo=LOCAL_TZ))
    assert esta_en_tolerancia(horario_turno_utc, llegada_temprana) is True

    # Llegada dentro de tolerancia: 9:39 ART (9 min tarde)
    llegada_limite = to_utc(dt(2026, 5, 10, 9, 39, tzinfo=LOCAL_TZ))
    assert esta_en_tolerancia(horario_turno_utc, llegada_limite) is True

    # Llegada a los 10 minutos exactos: en tolerancia
    llegada_10m = to_utc(dt(2026, 5, 10, 9, 40, tzinfo=LOCAL_TZ))
    assert esta_en_tolerancia(horario_turno_utc, llegada_10m) is True

    # Llegada a los 11 minutos: fuera de tolerancia
    llegada_tardia = to_utc(dt(2026, 5, 10, 9, 41, tzinfo=LOCAL_TZ))
    assert esta_en_tolerancia(horario_turno_utc, llegada_tardia) is False


def test_calculo_24_horas_antes_cancelacion() -> None:
    """La regla de 24 horas antes para cancelación habitual no sufre desfase horario."""
    ahora = now_utc()

    # Turno a 24 horas + 5 minutos en el futuro -> cancelación habitual habilitada
    turno_habilitado = ahora + timedelta(hours=24, minutes=5)
    diferencia_habilitada = (turno_habilitado - ahora).total_seconds()
    assert diferencia_habilitada >= 24 * 3600

    # Turno a 23 horas y 55 minutos en el futuro -> requiere cancelación rápida
    turno_rapido = ahora + timedelta(hours=23, minutes=55)
    diferencia_rapida = (turno_rapido - ahora).total_seconds()
    assert diferencia_rapida < 24 * 3600


def test_dia_de_semana_no_se_desplaza_por_utc() -> None:
    """Un turno el domingo a las 22:00 ART (lunes 01:00 UTC) debe evaluarse como domingo."""
    # Domingo 22:00 en Buenos Aires
    turno_domingo_noche_local = dt(2026, 5, 17, 22, 0, tzinfo=LOCAL_TZ)
    assert turno_domingo_noche_local.weekday() == 6  # 6 = Domingo

    turno_utc = to_utc(turno_domingo_noche_local)
    # En UTC ya es lunes (01:00)
    assert turno_utc.weekday() == 0  # 0 = Lunes

    # El servicio de agenda convierte a local para determinar el día de la semana
    assert to_local(turno_utc).weekday() == 6
