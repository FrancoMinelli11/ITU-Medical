from app.db.models.enums import EstadoTurno

TRANSICIONES_VALIDAS: dict[EstadoTurno, set[EstadoTurno]] = {
    EstadoTurno.RESERVADO: {
        EstadoTurno.EN_ESPERA,
        EstadoTurno.CANCELADO,
        EstadoTurno.AUSENTE,
    },
    EstadoTurno.EN_ESPERA: {
        EstadoTurno.ATENDIDO,
        EstadoTurno.CANCELADO,
    },
    EstadoTurno.ATENDIDO: set(),
    EstadoTurno.CANCELADO: set(),
    EstadoTurno.AUSENTE: set(),
}

ESTADOS_ACTIVOS: frozenset[EstadoTurno] = frozenset({EstadoTurno.RESERVADO, EstadoTurno.EN_ESPERA})

ESTADOS_EXCLUSION: frozenset[EstadoTurno] = frozenset(
    {EstadoTurno.RESERVADO, EstadoTurno.EN_ESPERA, EstadoTurno.ATENDIDO}
)


def puede_transicionar(actual: EstadoTurno, nuevo: EstadoTurno) -> bool:
    return nuevo in TRANSICIONES_VALIDAS[actual]
