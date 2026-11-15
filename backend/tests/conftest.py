"""Fixtures compartidas de la suite.

La configuración se resuelve **antes** de importar `app`: el singleton de
`Settings` se crea al importar el módulo, así que las variables de entorno deben
estar puestas acá (pytest carga este archivo antes de colectar los tests).

Cada worker de xdist usa su propia base (`turnos_test_<worker>`), creada y
migrada una vez por sesión. El estado se limpia entre tests con `TRUNCATE` y
`FLUSHDB` sobre el Redis de tests.
"""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import AsyncIterator, Callable, Iterator
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import pytest
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
# `override=False` respeta lo que ya define Compose: dentro del contenedor `api`
# las variables apuntan a la red interna (`db`, `redis`) y en el host a
# `localhost` con `DB_PORT`.
load_dotenv(RAIZ / ".env", override=False)

WORKER = os.environ.get("PYTEST_XDIST_WORKER", "main")
BASE_TEST = f"turnos_test_{WORKER}"


def _con_base(url: str, base: str) -> str:
    partes = urlsplit(url)
    return urlunsplit(partes._replace(path=f"/{base}"))


def _dsn(url: str) -> str:
    """Quita el driver de SQLAlchemy para quedarse con un DSN de asyncpg."""
    for prefijo in ("postgresql+asyncpg://", "postgresql+psycopg://"):
        if url.startswith(prefijo):
            return "postgresql://" + url[len(prefijo) :]
    return url


URL_TEST = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
if URL_TEST:
    URL_TEST = _con_base(URL_TEST, BASE_TEST)
    # La app, alembic y las fixtures apuntan todos a la base de tests.
    os.environ["TEST_DATABASE_URL"] = URL_TEST
    os.environ["DATABASE_URL"] = URL_TEST
    os.environ["ALEMBIC_DATABASE_URL"] = URL_TEST

REDIS_TEST = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")


def _redis_por_worker(url: str) -> str:
    """Un DB lógico de Redis por worker de xdist.

    Los workers comparten el servidor, pero no el estado: `estado_limpio` hace
    `FLUSHDB` entre tests, y si todos usaran el mismo DB se borrarían los
    contadores de rate limit y los refresh tokens de los demás.
    """
    partes = urlsplit(url)
    try:
        base = int((partes.path or "/0").lstrip("/") or 0)
    except ValueError:
        base = 0
    indice = 0
    if WORKER.startswith("gw") and WORKER[2:].isdigit():
        indice = int(WORKER[2:])
    return urlunsplit(partes._replace(path=f"/{max(0, base - indice)}"))


REDIS_TEST = _redis_por_worker(REDIS_TEST)
# `REDIS_URL` lo consume `/ready`: en el `.env` apunta al hostname de Compose
# (`redis`), que no resuelve desde el host. En tests todo va al Redis de test.
os.environ["REDIS_URL"] = REDIS_TEST
os.environ["RATE_LIMIT_STORAGE_URL"] = REDIS_TEST
os.environ["REFRESH_REDIS_URL"] = REDIS_TEST
# La cola de ARQ también al Redis de test: así los jobs de notificación se
# pueden inspeccionar (y `FLUSHDB` los limpia junto con el resto del estado).
os.environ["ARQ_REDIS_URL"] = REDIS_TEST

os.environ["APP_ENV"] = "test"
os.environ["SMTP_HOST"] = os.environ.get("TEST_SMTP_HOST", "localhost")
os.environ["SMTP_PORT"] = os.environ.get("TEST_SMTP_PORT", "1025")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")
os.environ["COOKIE_SECURE"] = "false"

# argon2 con parámetros baratos: cada login hashea y con los valores de
# producción la suite se vuelve lenta y consume 64 MiB por worker de xdist.
os.environ["ARGON2_TIME_COST"] = "1"
os.environ["ARGON2_MEMORY_COST"] = "8192"
os.environ["ARGON2_PARALLELISM"] = "1"

import asyncpg  # noqa: E402
from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from redis.asyncio import Redis  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.models.enums import RolUsuario  # noqa: E402
from app.db.models.paciente import Paciente  # noqa: E402
from app.db.models.usuario import Usuario  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402

BASE_URL = "http://localhost:8000"


def _admin_dsn() -> str:
    return _con_base(_dsn(URL_TEST), "postgres")


def _ejecutar_sql(dsn: str, sql: str) -> None:
    async def _run() -> None:
        conn = await asyncpg.connect(dsn)
        try:
            await conn.execute(sql)
        finally:
            await conn.close()

    asyncio.run(_run())


def _preservando_el_loop(funcion: Callable[[], None]) -> None:
    """`asyncio.run` deja `set_event_loop(None)`, y eso rompe el loop de sesión
    que arma pytest-asyncio. Se guarda y se restaura el loop vigente."""
    policy = asyncio.get_event_loop_policy()
    try:
        previo: asyncio.AbstractEventLoop | None = policy.get_event_loop()
    except RuntimeError:
        previo = None
    try:
        funcion()
    finally:
        policy.set_event_loop(previo)


@pytest.fixture(scope="session")
def base_migrada() -> Iterator[None]:
    """Crea la base del worker y la deja con la migración al día."""
    if not URL_TEST:
        pytest.skip("Sin TEST_DATABASE_URL ni DATABASE_URL configuradas")

    dsn_admin = _admin_dsn()
    try:
        _ejecutar_sql(dsn_admin, f'DROP DATABASE IF EXISTS "{BASE_TEST}" WITH (FORCE)')
        _ejecutar_sql(dsn_admin, f'CREATE DATABASE "{BASE_TEST}"')
    except (TimeoutError, OSError, asyncpg.PostgresError) as exc:
        pytest.skip(f"PostgreSQL no disponible: {type(exc).__name__}: {exc}")

    config = Config(str(RAIZ / "alembic.ini"))
    _preservando_el_loop(lambda: command.upgrade(config, "head"))
    yield


@pytest.fixture
async def estado_limpio(base_migrada: None) -> AsyncIterator[None]:
    async with SessionLocal() as session:
        # `CASCADE` limpia paciente, medico, turno, notificacion, auditoria y
        # los tokens de verificación/recuperación (todas cuelgan de usuario).
        await session.execute(text("TRUNCATE TABLE usuario, especialidad RESTART IDENTITY CASCADE"))
        await session.commit()

    redis = Redis.from_url(REDIS_TEST, decode_responses=True)
    try:
        await redis.flushdb()
    finally:
        await redis.aclose()

    yield


@pytest.fixture
async def client(estado_limpio: None) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE_URL) as cliente:
        yield cliente


@pytest.fixture
async def nuevo_client() -> AsyncIterator[object]:
    """Fábrica de clientes con jar propio (sesiones distintas en el mismo test)."""

    abiertos: list[AsyncClient] = []

    def _crear() -> AsyncClient:
        cliente = AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL)
        abiertos.append(cliente)
        return cliente

    yield _crear

    for cliente in abiertos:
        await cliente.aclose()


class FabricaUsuarios:
    """Crea usuarios (y su fila de paciente) para los tests."""

    def __init__(self) -> None:
        self._secuencia = 0

    def _siguiente(self) -> int:
        self._secuencia += 1
        return self._secuencia

    async def crear(
        self,
        *,
        rol: RolUsuario = RolUsuario.PACIENTE,
        password: str | None = "Password123!",
        dni: str | None = None,
        email: str | None = None,
        habilitado: bool = True,
        email_verificado: bool = True,
        debe_cambiar_password: bool = False,
        nombre: str = "Nombre",
        apellido: str = "Apellido",
        telefono: str | None = None,
        fecha_nacimiento: date | None = None,
    ) -> Usuario:
        numero = self._siguiente()
        dni_final = dni or f"2{numero:07d}"
        email_final = email or f"usuario{numero}@example.com"
        # `password=None` modela una cuenta creada por recepción: contraseña
        # temporal = DNI literal (decisión Q1 = A).
        password_final = dni_final if password is None else password

        async with SessionLocal() as session:
            usuario = Usuario(
                dni=dni_final,
                email=email_final,
                password_hash=hash_password(password_final),
                rol=rol,
                nombre=nombre,
                apellido=apellido,
                habilitado=habilitado,
                email_verificado=email_verificado,
                debe_cambiar_password=debe_cambiar_password,
            )
            session.add(usuario)
            await session.flush()
            if rol is RolUsuario.PACIENTE:
                session.add(
                    Paciente(
                        id_usuario=usuario.id_usuario,
                        telefono=telefono,
                        fecha_nacimiento=fecha_nacimiento,
                    )
                )
            await session.commit()
            return usuario


class SesionAuth:
    """Atajos de login/CSRF sobre un cliente httpx con su cookie jar."""

    def __init__(self, cliente: AsyncClient) -> None:
        self.cliente = cliente
        self.access = ""

    async def login(self, dni: str, password: str) -> dict[str, Any]:
        respuesta = await self.cliente.post(
            "/api/v1/auth/login", json={"dni": dni, "password": password}
        )
        assert respuesta.status_code == 200, respuesta.text
        datos: dict[str, Any] = respuesta.json()
        self.access = datos["access_token"]
        return datos

    @property
    def csrf(self) -> str:
        return self.cliente.cookies.get("csrf_token") or ""

    @property
    def bearer(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access}"}

    def mutacion(self) -> dict[str, str]:
        """Headers para un método no idempotente con sesión iniciada."""
        return {**self.bearer, "X-CSRF-Token": self.csrf}


@pytest.fixture
def sesion(client: AsyncClient) -> SesionAuth:
    return SesionAuth(client)


class BuzonDeCorreo:
    """Captura los envíos en lugar de tocar SMTP ni la cola de ARQ.

    Sustituye `notificacion_service.despachar` durante el test. Sirve para leer
    el token plano del enlace: en la base solo queda el hash (RN-31), así que el
    único lugar donde el token completo existe es el cuerpo del correo.
    """

    ASUNTO_VERIFICACION = "Verificá tu correo para reservar turnos"
    ASUNTO_RECUPERACION = "Restablecer tu contraseña"

    def __init__(self) -> None:
        self.envios: list[dict[str, str]] = []

    def registrar(self, *, destinatario: str, asunto: str, cuerpo: str) -> None:
        self.envios.append({"destinatario": destinatario, "asunto": asunto, "cuerpo": cuerpo})

    def de(self, email: str, asunto: str | None = None) -> list[dict[str, str]]:
        return [
            envio
            for envio in self.envios
            if envio["destinatario"] == email and (asunto is None or envio["asunto"] == asunto)
        ]

    def token(self, email: str, asunto: str | None = None) -> str:
        """Token del último correo (verificación por defecto) enviado a `email`."""
        envios = self.de(email, asunto or self.ASUNTO_VERIFICACION)
        assert envios, f"no se envió el correo esperado a {email}"
        encontrado = re.search(r"token=([A-Za-z0-9_\-]+)", envios[-1]["cuerpo"])
        assert encontrado, "el cuerpo del correo no incluye el enlace con token"
        return encontrado.group(1)


@pytest.fixture
def buzon(monkeypatch: pytest.MonkeyPatch) -> BuzonDeCorreo:
    from app.services import notificacion_service

    buzon = BuzonDeCorreo()

    async def _despachar(
        notificacion: object, *, destinatario: str, asunto: str, cuerpo: str
    ) -> bool:
        buzon.registrar(destinatario=destinatario, asunto=asunto, cuerpo=cuerpo)
        return True

    monkeypatch.setattr(notificacion_service, "despachar", _despachar)
    return buzon


@pytest.fixture
async def fabrica(estado_limpio: None) -> FabricaUsuarios:
    return FabricaUsuarios()
