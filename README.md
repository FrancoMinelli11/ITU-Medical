# Sistema de Turnos Médicos

Sistema web para la gestión administrativa de turnos de un centro médico.
El alcance y las reglas de negocio están en [`docs/requisitos.md`](docs/requisitos.md);
las decisiones de diseño de la FASE 2, en [`docs/diseno.md`](docs/diseno.md).

## Estado

- FASE 1: análisis cerrado.
- FASE 2: diseño técnico y andamiaje (este hito).
- FASE 3+: lógica de negocio, pendiente de aprobación.

El repositorio incluye modelos, migración inicial, contratos base y el entorno de
desarrollo. **No incluye todavía la lógica funcional de turnos.**

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

Credenciales del seed de desarrollo:

| Rol | Email | Contraseña |
|---|---|---|
| Administrador | `admin@turnos.local` | `Admin12345!` |
| Recepción | `recepcion@turnos.local` | `Recepcion123!` |
| Médico | `medico@turnos.local` | `Medico12345!` |
| Paciente | `paciente@turnos.local` | `Paciente123!` |

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
> unicidades parciales y el ciclo `downgrade base` + `upgrade head`.
> **Borra el esquema `public`** de la base indicada: usalo solo en local o CI.

## Arquitectura

```text
frontend (React + TS)  ->  /api/v1  ->  FastAPI  ->  PostgreSQL
                                      |-> Redis (rate limit, colas)
                                      |-> ARQ worker/scheduler -> Mailpit/SMTP
```

- `backend/app/api/v1`: endpoints.
- `backend/app/services`: reglas de negocio (FASE 3).
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
