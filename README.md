# Sistema de Turnos Médicos

Sistema web para la gestión administrativa de turnos de un centro médico.
El alcance y las reglas de negocio están en [`docs/requisitos.md`](docs/requisitos.md);
las decisiones de diseño de la FASE 2, en [`docs/diseno.md`](docs/diseno.md).

## Estado

- **Proyecto 100% Completado**: todas las fases y requerimientos implementados y verificados.
- **Backend**:
  - H1: Andamiaje, base de datos y esquema con PostgreSQL 16 y `btree_gist`.
  - H2.1 - H2.4: Autenticación completa (JWT en memoria + refresh rotativo httpOnly, CSRF double-submit, rate limiting, verificación de correo asíncrona, recuperación y cambio obligatorio en primer ingreso).
  - H3: Catálogo de especialidades, profesionales médicos, horarios habituales, bloqueos de agenda y cálculo de disponibilidad horaria (RF-04, RF-17, RF-18, RF-26).
  - H4: Reservas web y por recepción, prevención de solapamientos con exclusion constraints parciales atómicas, validación de reglas de agenda (RF-05, RF-06, RF-07, RF-25).
  - H5: Cancelación habitual (>= 24 hs) con liberación inmediata, solicitud rápida (< 24 hs) con motivo y resolución por recepción, cancelación administrativa (RF-08, RF-09, RF-10, RF-24).
  - H6: Recepción y sala de espera en tiempo real con algoritmo de orden de prioridad y tolerancia de 10 min, registro de ausencias individuales y cierre de jornada (RF-11, RF-12, RF-15).
  - H7: Atención médica (`EN_ESPERA` -> `ATENDIDO`) y notas clínicas administrativas de seguimiento confidenciales para rol médico/admin (RF-13, RF-14).
  - H8: Restricciones de Usuario Rojo por 30 días, bloqueo de turnos web y admisión presencial en recepción, evaluación dinámica sin cron (RF-16).
  - H9: Scheduler periódico ARQ de recordatorios automáticos 24 hs antes del turno y soporte integral de zona horaria `America/Argentina/Buenos_Aires` (RF-22, RNF-06).
  - Auditoría integral (RF-19) y matriz estricta de permisos en el servidor en cada endpoint (RNF-03).
- **Frontend**:
  - Portal de Pacientes: mis turnos, reserva paso a paso con slots disponibles, y cancelación habitual o rápida con modal contextual.
  - Portal de Recepción: sala de espera en vivo ordenada por prioridad (`Puntual`, `En tolerancia`, `Tardío`) y estados, búsqueda y alta rápida de pacientes por DNI, resolución de cancelaciones rápidas, ausencias y gestión de Usuario Rojo.
  - Portal Médico: agenda diaria de consultas asignadas, registro de atención en consultorio y notas clínicas de seguimiento.
  - Navegación responsive por roles, guard de rutas, manejo de errores RFC 7807 y suite de pruebas con MSW.
- **Pruebas y CI**:
  - 215 tests backend en `pytest` (100% passing).
  - 45 tests frontend en `vitest` (100% passing).
  - GitHub Actions CI verde en todos los builds, verificaciones y tests.

## Autenticación

| Paso | Llamada |
|---|---|
| Bootstrap CSRF | `GET /api/v1/auth/csrf` → cookie `csrf_token` (legible por el SPA) |
| Login | `POST /api/v1/auth/login` `{dni, password}` → access token (15 min) en el body + cookie `refresh_token` httpOnly |
| Renovar | `POST /api/v1/auth/refresh` con `X-CSRF-Token` → access nuevo, `refresh_token` y `csrf_token` rotados |
| Perfil | `GET /api/v1/auth/me` con `Authorization: Bearer <access>` |
| Logout | `POST /api/v1/auth/logout` con `X-CSRF-Token` → revoca la familia y borra cookies |
| Registro web | `POST /api/v1/auth/registro` `{dni, email, password, nombre, apellido, ...}` → `201`; envía el correo de verificación (Mailpit en desarrollo) |
| Verificar correo | `POST /api/v1/auth/verificar-email` `{token}` → `200`; reenvío con `POST /api/v1/auth/reenviar-verificacion` `{email}` (respuesta genérica, 3/hora) |
| Pacientes | `GET/POST /api/v1/pacientes` y `GET/PATCH /api/v1/pacientes/{id}` con rol recepción/administrador |
| Recuperar contraseña | `POST /api/v1/auth/recuperar-password` `{email, dni}` → `200` genérico; el enlace llega a Mailpit (3 solicitudes/hora) |
| Restablecer | `POST /api/v1/auth/restablecer-password` `{token, password}` → `200`; revoca todas las sesiones |
| Cambiar contraseña | `POST /api/v1/auth/cambiar-password` `{password_actual, password_nueva}` con Bearer + CSRF → `204` |
| Primer ingreso | `POST /api/v1/auth/primer-ingreso` `{password_nueva}` con Bearer + CSRF → `204` |

El access token va **solo en memoria** del SPA (nunca `localStorage`). Toda mutación
necesita `X-CSRF-Token` igual a la cookie; las rutas de entrada
(`/auth/login`, `/auth/registro`, `/auth/recuperar-password`,
`/auth/restablecer-password`, `/auth/verificar-email`,
`/auth/reenviar-verificacion`) están exentas. La cookie `csrf_token` usa `Path=/`
para que el SPA pueda leerla desde cualquier pantalla.

### Pantallas del SPA

| Ruta | Acceso | Contenido |
|---|---|---|
| `/login` | anónimos | DNI + contraseña; deriva a `/primer-ingreso` si corresponde |
| `/registro` | anónimos | Alta de paciente con verificación de correo |
| `/recuperar-password` | público | Correo + DNI, respuesta genérica |
| `/restablecer-password` | público | Token del correo + contraseña nueva |
| `/verificar-email` | público | Verificación automática y reenvío del enlace |
| `/` | sesión | Inicio con datos de la cuenta, acceso rápido por rol y logout |
| `/turnos` | paciente | Mis turnos asignados (próximos y pasados) con acción de cancelación |
| `/turnos/reservar` | paciente | Reserva de turnos por especialidad, profesional, fecha y horario disponible |
| `/recepcion` | recepción, admin | Sala de espera en vivo ordenada por prioridad, búsqueda y alta de pacientes, cancelaciones rápidas, ausencias y Usuario Rojo |
| `/medico` | médico, admin | Agenda de turnos asignados del día, registro de atención y notas clínicas |
| `/primer-ingreso` | sesión con cambio pendiente | CU-13, encierra al usuario hasta cambiarla |
| `/cambiar-password` | sesión | Cambio voluntario (revoca las sesiones abiertas) |

```bash
curl.exe -i -c cookies.txt http://localhost:8000/api/v1/auth/csrf
curl.exe -i -b cookies.txt -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login ^
  -H "Content-Type: application/json" -d "{\"dni\":\"20000001\",\"password\":\"Paciente123!\"}"
```

## Requisitos

- Docker con Compose.
- `uv` para backend, `pnpm` para frontend (o usarlos dentro de Docker).
- PostgreSQL 16 y Redis 7 se levantan con Compose.

## Puesta en marcha

```bash
cp .env.example .env          # Windows: Copy-Item .env.example .env
docker compose up -d
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed.py
```

Servicios:

| Servicio | URL |
|---|---|
| API / Swagger | http://localhost:8000/docs |
| Frontend | http://localhost:5173 |
| Mailpit | http://localhost:8025 |
| PostgreSQL | `localhost:5433` (mapeado a 5432 interno) |

`DB_PORT` define el puerto del host: el valor por defecto es **5433** porque en
este host de desarrollo `5432` lo ocupa un PostgreSQL nativo. El puerto interno
del contenedor es siempre `5432`, así que dentro de Compose nada cambia.

El entorno virtual del backend vive en `/opt/venv` dentro de la imagen, así el
bind mount del código no lo tapa. Al cambiar dependencias:

```bash
docker compose build api worker scheduler
```

Credenciales del seed de desarrollo (escenario S-14, todos con email verificado):

| Rol | Email | Contraseña |
|---|---|---|
| Administrador | `admin@turnos.local` | `Admin12345!` |
| Recepción 1 | `recepcion1@turnos.local` | `Recepcion123!` |
| Recepción 2 | `recepcion2@turnos.local` | `Recepcion123!` |
| Médico 1 (Clínica) | `medico1@turnos.local` | `Medico12345!` |
| Médico 2 (Cardiología) | `medico2@turnos.local` | `Medico12345!` |
| Médico 3 (Pediatría) | `medico3@turnos.local` | `Medico12345!` |
| Paciente 1 | `paciente1@turnos.local` | `Paciente123!` |
| Paciente 2 | `paciente2@turnos.local` | `Paciente123!` |

## Comandos útiles

```bash
# Backend
uv sync --project backend
uv run --project backend ruff check backend scripts
uv run --project backend ruff format --check backend scripts
uv run --project backend mypy backend/app
uv run --project backend pytest

# Migraciones
uv run --project backend alembic -c alembic.ini upgrade head
uv run --project backend alembic -c alembic.ini check      # modelos == esquema
uv run --project backend python scripts/verify_migration.py --url "$DATABASE_URL"

# Frontend
cd frontend
pnpm install
pnpm dev
pnpm lint
pnpm typecheck
pnpm test -- --run
pnpm build
```

> `scripts/verify_migration.py` comprueba contra PostgreSQL real las exclusion
> constraints por médico y paciente, los `CHECK` de DNI y duración, las
> unicidades parciales, la inmutabilidad de `rango_turno` y el ciclo
> `downgrade base` + `upgrade head` (21 comprobaciones).
> **Borra el esquema `public`** de la base indicada: usalo solo en local o CI.
> Dentro de Compose hay que apuntarlo a una base descartable:
>
> ```bash
> docker compose exec db psql -U postgres -c "CREATE DATABASE turnos_verify;"
> docker compose exec api python scripts/verify_migration.py \
>   --url postgresql://postgres:postgres@db:5432/turnos_verify
> docker compose exec db psql -U postgres -c "DROP DATABASE turnos_verify;"
> ```
>
> Sin `--url` el script levanta un PostgreSQL embebido con `pgserver`, que no es
> una dependencia del proyecto: en ese caso imprime las dos alternativas y sale
> con código 1 en lugar de fallar con un `ModuleNotFoundError`.

## Tests

`pytest` corre igual desde el host y desde el contenedor (`pytest.ini` se copia a
la imagen y además se monta en `api` para que el contenedor use el del repo),
incluidos los 21 checks de integración de la migración. La suite de integración
necesita `TEST_DATABASE_URL` y `TEST_REDIS_URL`; `backend/tests/conftest.py`
carga `.env`, así que:

- **host**: apunta a `localhost:${DB_PORT}` (por defecto `5433`) y usa el
  PostgreSQL de Compose;
- **contenedor `api`**: Compose redefine la variable a `db:5432` (red interna);
- **CI**: no hay `.env`, así que se usa el `DATABASE_URL` del job con el service
  de Postgres y `redis`.

Cada worker de xdist crea su propia base (`turnos_test_<worker>`), usa su propia
DB lógica de Redis y su propia base descartable para el test de migración, así que
`pytest -n auto` es seguro. Las fixtures de sesión comparten un único event loop
por worker: el engine async y los clientes Redis se reutilizan sin conexiones
atadas a un loop cerrado.

Ningún test se saltea por defecto. Se skipean solo si el PostgreSQL de
`TEST_DATABASE_URL` no está levantado (por ejemplo, con Compose caído) o si el
SMTP de Mailpit (`TEST_SMTP_HOST:TEST_SMTP_PORT`) no responde —lo necesitan los
tests de `test_notificaciones.py`—, y el motivo aparece en el resumen con
`pytest -rs`.


## Arquitectura

```text
frontend (React + TS)  ->  /api/v1  ->  FastAPI  ->  PostgreSQL
                                      |-> Redis (rate limit, colas)
                                      |-> ARQ worker/scheduler -> Mailpit/SMTP
```

- `backend/app/api/v1`: endpoints.
- `backend/app/services`: reglas de negocio (auth y pacientes implementados; el
  resto llega en la FASE 3).
- `backend/app/domain`: estados, transiciones y orden de atención.
- `backend/app/db/models`: modelo de datos.
- `backend/alembic`: migraciones, incluidas las exclusion constraints.
- `frontend/src/features`: pantallas por rol.
- `scripts`: seed, verificación de migración, backup y restore.

## Base de datos

La migración inicial crea `btree_gist`, los enums y las tablas del DER. Las
restricciones de exclusión por médico y por paciente se crean con `op.execute`
porque Alembic no las autogenera, y usan la función `IMMUTABLE`
`rango_turno(timestamptz, integer)`: `timestamptz + interval` es `STABLE` y
PostgreSQL no admite expresiones no inmutables dentro de un índice.

## Pruebas

- Backend: `pytest` + `pytest-asyncio` + `httpx.AsyncClient` + `factory-boy`.
- Frontend: Vitest + Testing Library + `msw`.
- El test de concurrencia se marca `@pytest.mark.serial` y se ejecuta sin xdist.
