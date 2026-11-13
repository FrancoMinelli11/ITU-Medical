# AGENTS.md

Instrucciones para agentes de código que trabajen en este repositorio.

## 1. Fuente de verdad

`docs/requisitos.md` es la fuente de verdad del dominio:

- Requerimientos funcionales **RF-01 … RF-27**
- Requerimientos no funcionales **RNF-01 … RNF-11**
- Reglas de negocio **RN-01 … RN-38**
- Casos de uso **CU-01 … CU-15**
- Estados y transiciones de turno
- DER completo (sección 13) y relaciones (sección 14)
- Plan de pruebas **P-01 … P-45**
- Metodología de 5 fases (sección 16)

**Leelo completo antes de escribir una línea de código.**
Si encontrás una contradicción entre este archivo y `docs/requisitos.md`,
gana `docs/requisitos.md`. Si la contradicción es con el stack o las
reglas de trabajo, gana este archivo.

## 2. Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.x async (`asyncpg`), Alembic,
  Pydantic v2, `uv`.
- **Frontend**: React 18 + TypeScript, Vite, React Router, TanStack Query,
  `react-hook-form` + `zod`, Tailwind CSS + shadcn/ui, `pnpm`.
- **Base de datos**: PostgreSQL 16 con `btree_gist`. Redis 7.
- **Worker / scheduler**: ARQ (async, compatible con FastAPI).
- **Tests backend**: `pytest` + `pytest-asyncio` + `httpx.AsyncClient` +
  `factory-boy` contra Postgres real (contenedor). `pytest-xdist` por defecto;
  test de concurrencia marcado `@pytest.mark.serial`.
- **Tests frontend**: Vitest + Testing Library + `msw`.
- **Entorno**: Docker Compose con servicios `api`, `worker`, `scheduler`,
  `web`, `db`, `redis`, `mailpit`. Healthchecks en `db` y `redis`.
- **Logging**: `structlog` (JSON) con `X-Request-ID` propagado.
- **Rate limiting**: `slowapi` sobre Redis.
- **Lint/format**: `ruff` + `mypy` (backend), `eslint` + `prettier` (frontend).
- **CI**: GitHub Actions (lint + type-check + test + build en cada PR).

## 3. Restricciones técnicas no negociables

Estas restricciones **complementan** `docs/requisitos.md`; no las repiten.
El agente debe verificarlas en cada entrega:

- **Exclusion constraints** en `TURNO`, una por `id_medico` y otra por
  `id_paciente`, ambas **parciales** sobre
  `estado IN ('RESERVADO','EN_ESPERA','ATENDIDO')`, con `btree_gist` +
  `tstzrange(fecha_hora, fecha_hora + duracion)`. Crear con
  `CREATE EXTENSION IF NOT EXISTS btree_gist` al inicio de la migración.
  `op.create_exclusion_constraint` no autogenera: usar `op.execute`.
- **Reservas transaccionales**: `SERIALIZABLE` o `READ COMMITTED` +
  `SELECT … FOR UPDATE`. Ante error, rollback total, sin turno parcial.
- **DNI**: `VARCHAR(8)`, `UNIQUE`, 7-8 dígitos. Nunca `INTEGER`.
- **Contraseñas**: `argon2id` (`argon2-cffi`). Primer login con cambio
  obligatorio para cuentas creadas por recepción (`debe_cambiar_password`).
- **Auth**: JWT de acceso corto + refresh rotativo en cookie `httpOnly`,
  `SameSite=Lax`, `Secure` en prod. CSRF double-submit (`X-CSRF-Token`)
  en métodos no idempotentes. **No** `localStorage`.
- **Permisos**: validados en el servidor en **cada** endpoint. Ocultar
  botones no cuenta.
- **Turnos nunca se borran**: `CANCELADO`/`AUSENTE`/`ATENDIDO` son finales.
- **Transiciones**: validar contra la tabla de `docs/requisitos.md` §10.
- **Auditoría**: toda operación crítica (reserva, cancelación, aprobación/
  rechazo, cambio de agenda, restricción, ausencia, nota, cambio de
  contraseña, verificación) escribe en `AUDITORIA`.
- **Usuario rojo**: evaluado por `fecha_fin` en cada request. Sin cron.
- **Zona horaria**: DB en UTC (`timestamptz`). Reglas (24 hs, tolerancia
  10 min, recordatorio 24 hs, día de semana) en
  `America/Argentina/Buenos_Aires`.
- **Notificaciones**: asíncronas vía ARQ, idempotentes
  (`UNIQUE (id_turno, tipo)` para confirmación y recordatorio), máximo
  3 reintentos con backoff exponencial. Fallo de envío **no aborta** la
  transacción principal.
- **Rate limits** de RN-37 aplicados en server (slowapi).
- **Recuperación de contraseña**: form pide email + DNI juntos. Respuesta
  genérica siempre. Tokens hasheados, un solo uso, 1 h de expiración.
- **Verificación de email**: tokens hasheados, un solo uso, 24 h.
  Cuentas creadas por recepción se marcan verificadas al crearse.

## 4. Reglas de trabajo

1. **Metodología secuencial** (5 fases, `docs/requisitos.md` §16).
   No avances de fase sin aprobación explícita.
2. **FASE 1 ahora**: **no escribas código**. Entregá:
   - (a) Plan de implementación por hitos con entregables y criterios de
     aceptación.
   - (b) Ambigüedades **residuales** que encuentres (las de
     `docs/requisitos.md` ya están resueltas).
   - (c) Suposiciones adicionales numeradas.
   - (d) Confirmación del DER (`docs/requisitos.md` §13) o correcciones
     propuestas.
   - (e) Contrato de API (endpoints, métodos, códigos, RFC 7807,
     paginación).
   - (f) Estructura de carpetas backend y frontend.
   - (g) `.env.example` completo.
   - (h) Plan de pruebas: mapeo P-01..P-45 a archivos de test.
   - (i) `docs/trazabilidad.md` inicial (RF/RN/P → módulo previsto).
   
   Esperá aprobación antes de FASE 2.
3. **Alcance cerrado**: nada de historia clínica, diagnósticos, recetas,
   tratamientos, facturación, emergencias ni farmacia.
4. **Trazabilidad**: cada RF, RN y P numerado en `docs/requisitos.md`
   debe poder rastrearse a código y a test.
5. **Commits**: Conventional Commits. Un commit al cerrar cada hito.
   PRs contra `main` con CI verde.
6. **Secretos**: solo por variables de entorno. `.env.example` versionado,
   `.env` ignorado.
7. **Idioma**: interfaz y nombres de tablas/campos en español (como el DER).

## 5. Cómo correr (a crear en FASE 2)

```bash
cp .env.example .env
docker compose up -d
alembic upgrade head
python scripts/seed.py
# API:      http://localhost:8000/docs
# Frontend: http://localhost:5173
# Mailpit:  http://localhost:8025