"""Verificación end-to-end de la migración inicial contra PostgreSQL real.

ATENCIÓN: elimina y recrea el esquema `public` de la base indicada. Usalo solo
contra bases descartables (local o CI), nunca contra datos reales.

Comprueba:
  1. `alembic upgrade head`,
  2. las exclusion constraints por médico y por paciente,
  3. los CHECK de DNI y de duración,
  4. la unicidad parcial de notificaciones y de restricción activa,
  5. `alembic downgrade base` y un nuevo `upgrade head`.

Uso:
    python scripts/verify_migration.py --url postgresql://postgres@localhost:5432/turnos

Si se omite `--url`, levanta un PostgreSQL embebido con `pgserver`.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import asyncpg

REPO_ROOT = Path(__file__).resolve().parents[1]

INSERT_USUARIO = (
    "INSERT INTO usuario (id_usuario, dni, email, password_hash, rol, nombre, apellido)"
    " VALUES ($1, $2, $3, 'x', $4, $5, 'Apellido')"
)
INSERT_PACIENTE = (
    "INSERT INTO paciente (id_paciente, id_usuario, fecha_nacimiento) VALUES ($1, $2, $3)"
)
INSERT_MEDICO = (
    "INSERT INTO medico (id_medico, id_usuario, id_especialidad, matricula) VALUES ($1, $2, $3, $4)"
)
INSERT_TURNO = (
    "INSERT INTO turno (id_paciente, id_medico, fecha_hora, duracion_minutos,"
    " estado, id_usuario_creador) VALUES ($1, $2, $3, $4, $5, $6)"
)
INSERT_RESTRICCION = (
    "INSERT INTO restriccion_usuario (id_usuario, motivo, fecha_fin,"
    " id_usuario_creador) VALUES ($1, $2, $3, $4)"
)

fallos: list[str] = []
ok: list[str] = []


def check(nombre: str, condicion: bool, detalle: str = "") -> None:
    if condicion:
        ok.append(nombre)
        print(f"  OK    {nombre}")
    else:
        fallos.append(f"{nombre} {detalle}".strip())
        print(f"  FALLA {nombre} {detalle}")


async def espera_exclusion(
    conn: asyncpg.Connection,
    nombre: str,
    args: tuple[Any, ...],
) -> None:
    """El INSERT debe ser rechazado por una exclusion constraint."""
    try:
        await conn.execute(INSERT_TURNO, *args)
    except asyncpg.ExclusionViolationError:
        check(nombre, True)
    except asyncpg.PostgresError as exc:
        check(nombre, False, f"(error inesperado: {type(exc).__name__}: {exc})")
    else:
        check(nombre, False, "(se aceptó el solapamiento)")


def run_alembic(accion: str, url: str) -> subprocess.CompletedProcess[str]:
    destino = "base" if accion == "downgrade" else "head"
    env = {**os.environ, "DATABASE_URL": url, "ALEMBIC_DATABASE_URL": url}
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", accion, destino],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


async def verificar(dsn: str) -> None:
    url = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    reset = await asyncpg.connect(dsn)
    try:
        await reset.execute("DROP SCHEMA public CASCADE")
        await reset.execute("CREATE SCHEMA public")
    finally:
        await reset.close()

    print("\n[1] alembic upgrade head")
    resultado = run_alembic("upgrade", url)
    if resultado.returncode != 0:
        print(resultado.stdout[-3000:])
        print(resultado.stderr[-3000:])
        fallos.append("alembic upgrade head")
        return
    print("  OK    migración aplicada")

    conn = await asyncpg.connect(dsn)
    try:
        await _verificar_estructura(conn)
        ids = await _verificar_datos(conn)
        await _verificar_exclusiones(conn, ids)
        await _verificar_checks(conn, ids)
        await _verificar_unicidades(conn, ids)
        await _verificar_inmutabilidad(conn, ids)
    finally:
        await conn.close()

    print("\n[10] downgrade base y upgrade head")
    resultado = run_alembic("downgrade", url)
    check("downgrade base", resultado.returncode == 0, resultado.stderr[-500:])
    resultado = run_alembic("upgrade", url)
    check(
        "upgrade head tras downgrade",
        resultado.returncode == 0,
        resultado.stderr[-500:],
    )


async def _verificar_estructura(conn: asyncpg.Connection) -> None:
    print("\n[2] estructura")
    tablas = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    nombres = {registro["tablename"] for registro in tablas}
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
        "alembic_version",
    }
    check(
        "14 tablas del DER + alembic_version",
        nombres == esperadas,
        f"(faltan: {sorted(esperadas - nombres)}, sobran: {sorted(nombres - esperadas)})",
    )

    extensiones = await conn.fetch("SELECT extname FROM pg_extension")
    check("btree_gist instalada", "btree_gist" in {r["extname"] for r in extensiones})

    constraints = await conn.fetch("SELECT conname FROM pg_constraint WHERE contype = 'x'")
    exclusiones = {registro["conname"] for registro in constraints}
    check(
        "exclusion constraints por médico y por paciente",
        {"ex_turno_medico", "ex_turno_paciente"} <= exclusiones,
        f"(encontradas: {sorted(exclusiones)})",
    )

    funciones = await conn.fetch(
        "SELECT proname, provolatile FROM pg_proc WHERE proname = 'rango_turno'"
    )
    check(
        "rango_turno es IMMUTABLE",
        len(funciones) == 1 and funciones[0]["provolatile"] in (b"i", "i"),
    )


async def _verificar_datos(conn: asyncpg.Connection) -> dict[str, Any]:
    print("\n[3] datos base")
    ids: dict[str, Any] = {
        "pac1": uuid.uuid4(),
        "pac2": uuid.uuid4(),
        "med1": uuid.uuid4(),
        "med2": uuid.uuid4(),
        "esp": uuid.uuid4(),
        "user_med": uuid.uuid4(),
        "user_maker": uuid.uuid4(),
    }

    await conn.execute(
        "INSERT INTO especialidad (id_especialidad, nombre) VALUES ($1, 'Clínica')",
        ids["esp"],
    )

    usuarios = [
        (ids["user_med"], "11111111", "m@test.local", "MEDICO", "Med"),
        (ids["user_maker"], "22222222", "r@test.local", "RECEPCIONISTA", "Rec"),
    ]
    for user_id, dni, email, rol, nombre in usuarios:
        await conn.execute(INSERT_USUARIO, user_id, dni, email, rol, nombre)

    pacientes = [
        (ids["pac1"], uuid.uuid4(), "33333333", "p1@test.local", date(1990, 1, 1)),
        (ids["pac2"], uuid.uuid4(), "44444444", "p2@test.local", date(1991, 2, 2)),
    ]
    for paciente_id, user_id, dni, email, nacimiento in pacientes:
        await conn.execute(INSERT_USUARIO, user_id, dni, email, "PACIENTE", "Pac")
        await conn.execute(INSERT_PACIENTE, paciente_id, user_id, nacimiento)

    medicos = [
        (ids["med1"], ids["user_med"], "MP-1"),
        (ids["med2"], ids["user_maker"], "MP-2"),
    ]
    for medico_id, user_id, matricula in medicos:
        await conn.execute(INSERT_MEDICO, medico_id, user_id, ids["esp"], matricula)

    check("datos base insertados", True)
    return ids


async def _verificar_exclusiones(conn: asyncpg.Connection, ids: dict[str, Any]) -> None:
    print("\n[4] exclusion constraints")
    base = datetime(2030, 5, 1, 12, 0, tzinfo=UTC)
    maker = ids["user_maker"]

    await conn.execute(INSERT_TURNO, ids["pac1"], ids["med1"], base, 30, "RESERVADO", maker)

    await espera_exclusion(
        conn,
        "mismo médico solapado -> rechazado",
        (ids["pac2"], ids["med1"], base + timedelta(minutes=15), 30, "RESERVADO", maker),
    )
    await espera_exclusion(
        conn,
        "mismo paciente solapado -> rechazado",
        (ids["pac1"], ids["med2"], base + timedelta(minutes=15), 30, "RESERVADO", maker),
    )

    await conn.execute(
        INSERT_TURNO,
        ids["pac2"],
        ids["med1"],
        base + timedelta(minutes=30),
        30,
        "RESERVADO",
        maker,
    )
    check("turno contiguo del mismo médico -> aceptado", True)

    await conn.execute(
        INSERT_TURNO,
        ids["pac1"],
        ids["med2"],
        base + timedelta(minutes=30),
        30,
        "RESERVADO",
        maker,
    )
    check("misma hora con otro médico -> aceptado", True)

    print("\n[5] estados exentos de la exclusión")
    await conn.execute(
        INSERT_TURNO,
        ids["pac2"],
        ids["med1"],
        base + timedelta(hours=5),
        30,
        "CANCELADO",
        maker,
    )
    turno_id = await conn.fetchval(
        INSERT_TURNO + " RETURNING id_turno",
        ids["pac1"],
        ids["med1"],
        base + timedelta(hours=5),
        30,
        "RESERVADO",
        maker,
    )
    check("un turno CANCELADO no bloquea el horario", turno_id is not None)
    ids["turno"] = turno_id


async def _verificar_checks(conn: asyncpg.Connection, ids: dict[str, Any]) -> None:
    print("\n[6] CHECK constraints")
    casos = [
        (
            "DNI de 6 dígitos -> rechazado",
            "INSERT INTO usuario (dni, email, password_hash, rol, nombre, apellido)"
            " VALUES ('123456', 'corto@test.local', 'x', 'PACIENTE', 'N', 'A')",
            (),
        ),
        (
            "DNI con letras -> rechazado",
            "INSERT INTO usuario (dni, email, password_hash, rol, nombre, apellido)"
            " VALUES ('1234567A', 'letras@test.local', 'x', 'PACIENTE', 'N', 'A')",
            (),
        ),
        (
            "duración cero -> rechazada",
            INSERT_TURNO,
            (
                ids["pac1"],
                ids["med1"],
                datetime(2031, 1, 1, 12, 0, tzinfo=UTC),
                0,
                "RESERVADO",
                ids["user_maker"],
            ),
        ),
    ]
    for descripcion, sql, args in casos:
        try:
            await conn.execute(sql, *args)
        except asyncpg.IntegrityConstraintViolationError:
            check(descripcion, True)
        else:
            check(descripcion, False, "(se aceptó)")


async def _verificar_unicidades(conn: asyncpg.Connection, ids: dict[str, Any]) -> None:
    print("\n[7] unicidad parcial de notificaciones")
    duplicado_rechazado = False
    for _ in range(2):
        try:
            await conn.execute(
                "INSERT INTO notificacion (tipo, id_turno) VALUES ('CONFIRMACION_TURNO', $1)",
                ids["turno"],
            )
        except asyncpg.UniqueViolationError:
            duplicado_rechazado = True
    check("confirmación duplicada -> rechazada", duplicado_rechazado)

    print("\n[8] restricción activa única por usuario")
    ahora = datetime.now(UTC)
    await conn.execute(
        INSERT_RESTRICCION,
        ids["user_maker"],
        "motivo",
        ahora + timedelta(days=10),
        ids["user_maker"],
    )
    try:
        await conn.execute(
            INSERT_RESTRICCION,
            ids["user_maker"],
            "otro",
            ahora + timedelta(days=20),
            ids["user_maker"],
        )
    except asyncpg.UniqueViolationError:
        check("segunda restricción activa -> rechazada", True)
    else:
        check("segunda restricción activa -> rechazada", False)

    await conn.execute(
        "UPDATE restriccion_usuario SET activa = false WHERE id_usuario = $1",
        ids["user_maker"],
    )
    await conn.execute(
        INSERT_RESTRICCION,
        ids["user_maker"],
        "nueva",
        ahora + timedelta(days=5),
        ids["user_maker"],
    )
    check("nueva restricción tras desactivar la anterior -> aceptada", True)


async def _verificar_inmutabilidad(conn: asyncpg.Connection, ids: dict[str, Any]) -> None:
    """Valida el supuesto del workaround: el cálculo en UTC es inmutable y estable."""
    print("\n[9] inmutabilidad y zona horaria")
    base = datetime(2032, 3, 15, 10, 0, tzinfo=UTC)
    zonas = ["UTC", "America/Argentina/Buenos_Aires", "America/New_York", "Asia/Tokyo"]

    valores = []
    for zona in zonas:
        await conn.execute(f"SET TIME ZONE '{zona}'")
        valores.append(await conn.fetchval("SELECT rango_turno($1, $2)", base, 45))

    await conn.execute("SET TIME ZONE 'UTC'")
    primero = valores[0]
    check(
        "rango_turno no depende de la zona horaria de la sesión",
        all(valor == primero for valor in valores),
        f"({[str(valor) for valor in valores]})",
    )

    referencia = await conn.fetchval(
        "SELECT tstzrange($1::timestamptz, $1::timestamptz + make_interval(mins => $2))",
        base,
        45,
    )
    check(
        "coincide con la aritmética absoluta de minutos (UTC)",
        primero == referencia,
        f"(calculado: {primero}, referencia: {referencia})",
    )

    await conn.execute(
        INSERT_TURNO, ids["pac1"], ids["med1"], base, 45, "RESERVADO", ids["user_maker"]
    )
    await conn.execute("SET TIME ZONE 'Asia/Tokyo'")
    await espera_exclusion(
        conn,
        "el solapamiento se detecta aunque cambie la zona de la sesión",
        (
            ids["pac2"],
            ids["med1"],
            base + timedelta(minutes=10),
            45,
            "RESERVADO",
            ids["user_maker"],
        ),
    )
    await conn.execute("SET TIME ZONE 'UTC'")


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        help="URL de un PostgreSQL ya iniciado (postgresql://...). "
        "Si se omite, se levanta uno embebido con `pgserver`.",
    )
    args = parser.parse_args()

    servidor = None
    if args.url:
        dsn = args.url.replace("+asyncpg", "")
    else:
        # `pgserver` no se distribuye con la aplicación y además no puede correr
        # como root dentro del contenedor: en vez de fallar con un traceback de
        # import, se explica cómo continuar.
        try:
            import pgserver
        except ModuleNotFoundError:
            print(
                "Error: pgserver no está instalado y no se pasó --url.\n"
                "Opciones:\n"
                "  1. Pasar una URL explícita: --url postgresql://user:pass@host:port/db\n"
                "  2. Correr la suite equivalente:\n"
                "     pytest backend/tests/integration/test_migration.py\n"
                "     (usa TEST_DATABASE_URL apuntando a un PostgreSQL descartable)",
                file=sys.stderr,
            )
            return 1

        servidor = pgserver.get_server(tempfile.mkdtemp(prefix="pgverify_"), cleanup_mode="delete")
        dsn = servidor.get_uri()

    try:
        print(f"PostgreSQL: {dsn.split('?')[0]}")
        await verificar(dsn)
    finally:
        if servidor is not None:
            servidor.cleanup()

    print(f"\nResultado: {len(ok)} OK, {len(fallos)} fallas")
    for fallo in fallos:
        print(f"  - {fallo}")
    return 0 if not fallos else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
