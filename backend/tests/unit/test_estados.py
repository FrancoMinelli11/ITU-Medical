import pytest

from app.db.models.enums import EstadoTurno
from app.domain.estados import (
    ESTADOS_ACTIVOS,
    ESTADOS_EXCLUSION,
    TRANSICIONES_VALIDAS,
    puede_transicionar,
)


def test_transiciones_permitidas() -> None:
    assert puede_transicionar(EstadoTurno.RESERVADO, EstadoTurno.EN_ESPERA)
    assert puede_transicionar(EstadoTurno.RESERVADO, EstadoTurno.CANCELADO)
    assert puede_transicionar(EstadoTurno.RESERVADO, EstadoTurno.AUSENTE)
    assert puede_transicionar(EstadoTurno.EN_ESPERA, EstadoTurno.ATENDIDO)
    assert puede_transicionar(EstadoTurno.EN_ESPERA, EstadoTurno.CANCELADO)


@pytest.mark.parametrize(
    ("actual", "nuevo"),
    [
        (EstadoTurno.ATENDIDO, EstadoTurno.RESERVADO),
        (EstadoTurno.CANCELADO, EstadoTurno.RESERVADO),
        (EstadoTurno.AUSENTE, EstadoTurno.EN_ESPERA),
        (EstadoTurno.RESERVADO, EstadoTurno.ATENDIDO),
    ],
)
def test_transiciones_invalidas(actual: EstadoTurno, nuevo: EstadoTurno) -> None:
    assert not puede_transicionar(actual, nuevo)


def test_estados_terminales() -> None:
    for estado in (EstadoTurno.ATENDIDO, EstadoTurno.CANCELADO, EstadoTurno.AUSENTE):
        assert TRANSICIONES_VALIDAS[estado] == set()


def test_conjuntos_de_estados() -> None:
    assert ESTADOS_ACTIVOS == {EstadoTurno.RESERVADO, EstadoTurno.EN_ESPERA}
    assert ESTADOS_EXCLUSION == {
        EstadoTurno.RESERVADO,
        EstadoTurno.EN_ESPERA,
        EstadoTurno.ATENDIDO,
    }
