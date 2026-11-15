"""Algoritmo de cálculo de orden de atención y tolerancia (RF-12, RN-15..RN-19).

Criterio:
1. Primero los pacientes que llegaron dentro de la tolerancia (<= 10 min posteriores
   al horario programado), ordenados por horario programado del turno. Llegar antes
   no permite adelantar a un turno previo.
2. Luego los pacientes que llegaron fuera de la tolerancia (> 10 min), ordenados
   por hora exacta de llegada.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol

TOLERANCIA_MINUTOS: int = 10


class TurnoEnEsperaProtocol(Protocol):
    fecha_hora: datetime
    fecha_hora_llegada: datetime | None


def esta_en_tolerancia(fecha_hora: datetime, fecha_hora_llegada: datetime | None) -> bool:
    """Verifica si el paciente llegó dentro de los 10 minutos de tolerancia (RF-12)."""
    if fecha_hora_llegada is None:
        return False
    tolerancia_maxima = fecha_hora + timedelta(minutes=TOLERANCIA_MINUTOS)
    return fecha_hora_llegada <= tolerancia_maxima


def clave_orden_atencion(
    turno: TurnoEnEsperaProtocol,
) -> tuple[int, datetime, datetime]:
    """Genera la tupla de ordenamiento estricta para la sala de espera."""
    en_tol = esta_en_tolerancia(turno.fecha_hora, turno.fecha_hora_llegada)
    llegada = turno.fecha_hora_llegada or turno.fecha_hora

    if en_tol:
        # Grupo 0: dentro de tolerancia -> ordenado por turno programado
        return (0, turno.fecha_hora, llegada)
    # Grupo 1: fuera de tolerancia -> ordenado por hora real de llegada
    return (1, llegada, turno.fecha_hora)


def ordenar_pacientes_en_espera[T: TurnoEnEsperaProtocol](turnos: list[T]) -> list[T]:
    """Ordena una lista de turnos en espera según la prioridad de atención de RF-12."""
    return sorted(turnos, key=clave_orden_atencion)
