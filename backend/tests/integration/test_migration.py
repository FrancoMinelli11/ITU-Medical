"""Los 21 checks de `scripts/verify_migration.py` como tests de integración.

El script no tiene efectos colaterales al importarse (solo define constantes y
funciones; la ejecución vive bajo `if __name__ == "__main__"`), así que se puede
importar como módulo. Cada check queda como un test independiente: si uno falla,
el nombre del test dice cuál.

Fixture: crea una base descartable en el mismo servidor configurado, aplica la
migración corriendo el flujo completo del script y la elimina al terminar. Nunca
toca la base de la aplicación.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.verify_migration as verify  # noqa: E402

pytestmark = pytest.mark.integration

BASE_TEMPORAL = "turnos_test_migration"

# Nombres exactos que produce el script. Se listan para que cada uno sea un test
# con nombre propio y para detectar si el script deja de comprobar algo.
CHECKS_ESPERADOS = [
    # [2] estructura
    "14 tablas del DER + alembic_version",
    "btree_gist instalada",
    "exclusion constraints por médico y por paciente",
    "rango_turno es IMMUTABLE",
    # [3] datos base
    "datos base insertados",
    # [4] exclusion constraints
    "mismo médico solapado -> rechazado",
    "mismo paciente solapado -> rechazado",
    "turno contiguo del mismo médico -> aceptado",
    "misma hora con otro médico -> aceptado",
    # [5] estados exentos
    "un turno CANCELADO no bloquea el horario",
    # [6] CHECK constraints
    "DNI de 6 dígitos -> rechazado",
    "DNI con letras -> rechazado",
    "duración cero -> rechazada",
    # [7] unicidad parcial
    "confirmación duplicada -> rechazada",
    # [8] restricción activa única
    "segunda restricción activa -> rechazada",
    "nueva restricción tras desactivar la anterior -> aceptada",
    # [9] inmutabilidad y zona horaria
    "rango_turno no depende de la zona horaria de la sesión",
    "coincide con la aritmética absoluta de minutos (UTC)",
    "el solapamiento se detecta aunque cambie la zona de la sesión",
    # [10] downgrade / upgrade
    "downgrade base",
    "upgrade head tras downgrade",
]


def _url_configurada() -> str:
    return os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or ""


def _dsn(url: str) -> str:
    """Quita el driver de SQLAlchemy para quedarse con un DSN de asyncpg."""
    for prefijo in ("postgresql+asyncpg://", "postgresql+psycopg://"):
        if url.startswith(prefijo):
            return "postgresql://" + url[len(prefijo) :]
    return url


def _con_base(dsn: str, base: str) -> str:
    partes = urlsplit(dsn)
    return urlunsplit(partes._replace(path=f"/{base}"))


async def _administrar(dsn_admin: str, sql: str) -> None:
    conn = await asyncpg.connect(dsn_admin)
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


def _ejecutar(dsn_admin: str, sql: str) -> None:
    asyncio.run(_administrar(dsn_admin, sql))


@pytest.fixture(scope="session")
def resultados_migracion() -> dict[str, Any]:
    url = _url_configurada()
    if not url:
        pytest.skip("Sin TEST_DATABASE_URL ni DATABASE_URL configuradas")

    dsn = _dsn(url)
    dsn_admin = _con_base(dsn, "postgres")

    try:
        _ejecutar(dsn_admin, f"DROP DATABASE IF EXISTS {BASE_TEMPORAL} WITH (FORCE)")
        _ejecutar(dsn_admin, f"CREATE DATABASE {BASE_TEMPORAL}")
    except (TimeoutError, OSError, asyncpg.PostgresError) as exc:
        pytest.skip(f"PostgreSQL no disponible: {type(exc).__name__}: {exc}")

    dsn_temporal = _con_base(dsn, BASE_TEMPORAL)

    verify.ok.clear()
    verify.fallos.clear()
    try:
        asyncio.run(verify.verificar(dsn_temporal))
        resultado: dict[str, Any] = {"ok": list(verify.ok), "fallos": list(verify.fallos)}
    finally:
        _ejecutar(dsn_admin, f"DROP DATABASE IF EXISTS {BASE_TEMPORAL} WITH (FORCE)")

    return resultado


@pytest.mark.parametrize("nombre", CHECKS_ESPERADOS)
def test_check_de_migracion(nombre: str, resultados_migracion: dict[str, Any]) -> None:
    assert nombre in resultados_migracion["ok"], (
        f"check no superado: {nombre}. Fallos: {resultados_migracion['fallos']}"
    )


def test_cantidad_de_checks_y_sin_fallas(resultados_migracion: dict[str, Any]) -> None:
    assert resultados_migracion["fallos"] == []
    assert len(resultados_migracion["ok"]) == len(CHECKS_ESPERADOS)
